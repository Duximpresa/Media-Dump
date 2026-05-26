import os
import queue
import shutil
import threading
import time
from pathlib import Path

from .hash_utils import files_match_sha256
from .models import (
    ACTION_COPY,
    ACTION_COPY_RENAMED,
    ACTION_ERROR,
    ACTION_SKIP_DUPLICATE,
    CopyStats,
    ImportPlan,
    ImportPlanItem,
    SourceFile,
)

BUFFER_SIZE = 16 * 1024 * 1024
PROGRESS_INTERVAL_SECONDS = 0.2
COPIED_LOG_INTERVAL = 20


def copy_file_with_progress(
    source: SourceFile,
    destination: Path,
    stats: CopyStats,
    events: queue.Queue,
    started_at: float,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_destination = destination.with_name(f"{destination.name}.copying")
    if temporary_destination.exists():
        temporary_destination.unlink()

    last_emit_at = time.monotonic()
    bytes_since_emit = 0

    try:
        with source.path.open("rb") as source_handle, temporary_destination.open("wb") as dest_handle:
            while True:
                chunk = source_handle.read(BUFFER_SIZE)
                if not chunk:
                    break
                dest_handle.write(chunk)
                chunk_size = len(chunk)
                stats.processed_bytes += chunk_size
                bytes_since_emit += chunk_size

                now = time.monotonic()
                if now - last_emit_at >= PROGRESS_INTERVAL_SECONDS:
                    stats.current_speed_bps = bytes_since_emit / (now - last_emit_at)
                    stats.elapsed_seconds = now - started_at
                    stats.average_speed_bps = stats.processed_bytes / max(stats.elapsed_seconds, 0.001)
                    events.put(("progress", stats))
                    last_emit_at = now
                    bytes_since_emit = 0

        shutil.copystat(source.path, temporary_destination)
        os.replace(temporary_destination, destination)
    except Exception:
        if temporary_destination.exists():
            temporary_destination.unlink()
        raise


def verify_copy(item: ImportPlanItem, stats: CopyStats, events: queue.Queue) -> bool:
    events.put(("verifying", str(item.destination), stats))
    if files_match_sha256(item.source.path, item.destination):
        stats.verify_success += 1
        return True

    stats.verify_failed += 1
    stats.failed += 1
    events.put(("log", f"校验失败：{item.source.path} -> {item.destination}"))
    return False


def finish_progress(stats: CopyStats, started_at: float, events: queue.Queue) -> None:
    now = time.monotonic()
    stats.elapsed_seconds = now - started_at
    stats.average_speed_bps = stats.processed_bytes / max(stats.elapsed_seconds, 0.001)
    stats.current_speed_bps = stats.average_speed_bps
    events.put(("progress", stats))


def copy_import_plan(
    plan: ImportPlan,
    cancel_event: threading.Event,
    events: queue.Queue,
) -> CopyStats:
    stats = CopyStats(
        total_files=plan.summary.total_files,
        total_bytes=plan.summary.total_bytes,
    )
    events.put(("total", stats.total_files, stats.total_bytes))
    if stats.total_files == 0:
        events.put(("done", stats))
        return stats

    started_at = time.monotonic()
    copy_actions = {ACTION_COPY, ACTION_COPY_RENAMED}

    for item in plan.items:
        if cancel_event.is_set():
            stats.cancelled = True
            break

        stats.processed_files += 1
        events.put(("current", str(item.source.path), stats))

        try:
            if item.action == ACTION_SKIP_DUPLICATE:
                stats.skipped += 1
                stats.processed_bytes += item.source.size
                events.put(("log", f"跳过重复文件：{item.destination}"))
            elif item.action == ACTION_ERROR:
                stats.failed += 1
                events.put(("log", f"计划错误：{item.source.path}，原因：{item.reason}"))
            elif item.action in copy_actions:
                if item.action == ACTION_COPY_RENAMED:
                    stats.renamed += 1
                    events.put(("log", f"自动改名：{item.original_destination} -> {item.destination}"))

                copy_file_with_progress(item.source, item.destination, stats, events, started_at)
                if verify_copy(item, stats, events):
                    stats.copied += 1
                    if stats.copied <= 5 or stats.copied % COPIED_LOG_INTERVAL == 0:
                        events.put(("log", f"已复制并校验 {stats.copied} 个文件，最新：{item.destination}"))
            else:
                stats.failed += 1
                events.put(("log", f"未知计划动作：{item.action}，文件：{item.source.path}"))
        except Exception as exc:
            stats.failed += 1
            events.put(("log", f"复制失败：{item.source.path}，原因：{exc}"))

        finish_progress(stats, started_at, events)

    if cancel_event.is_set():
        stats.cancelled = True

    stats.remaining_files = max(stats.total_files - stats.processed_files, 0)
    events.put(("done", stats))
    return stats


def copy_files(
    source_dir: Path,
    target_dir: Path,
    extensions: set[str] | None,
    template: str,
    cancel_event: threading.Event,
    events: queue.Queue,
) -> CopyStats:
    from .planner import build_import_plan

    try:
        plan = build_import_plan(source_dir, target_dir, extensions, template)
    except OSError as exc:
        stats = CopyStats()
        events.put(("fatal", f"扫描源文件夹失败：{exc}"))
        return stats
    return copy_import_plan(plan, cancel_event, events)

import os
import queue
import shutil
import threading
import time
from pathlib import Path

from .models import CopyStats, SourceFile
from .scanner import iter_matching_files
from .templates import build_target_path

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


def copy_files(
    source_dir: Path,
    target_dir: Path,
    extensions: set[str] | None,
    template: str,
    cancel_event: threading.Event,
    events: queue.Queue,
) -> CopyStats:
    stats = CopyStats()
    try:
        files = iter_matching_files(source_dir, extensions)
    except OSError as exc:
        events.put(("fatal", f"扫描源文件夹失败：{exc}"))
        return stats

    stats.total_files = len(files)
    stats.total_bytes = sum(source.size for source in files)
    events.put(("total", stats.total_files, stats.total_bytes))
    if stats.total_files == 0:
        events.put(("done", stats))
        return stats

    started_at = time.monotonic()
    for source in files:
        if cancel_event.is_set():
            stats.cancelled = True
            break

        stats.processed_files += 1
        events.put(("current", str(source.path), stats))

        try:
            destination = build_target_path(source.path, target_dir, template)
            if destination.exists():
                stats.skipped += 1
                stats.processed_bytes += source.size
                events.put(("log", f"跳过已存在：{destination}"))
            else:
                copy_file_with_progress(source, destination, stats, events, started_at)
                stats.copied += 1
                if stats.copied <= 5 or stats.copied % COPIED_LOG_INTERVAL == 0:
                    events.put(("log", f"已复制 {stats.copied} 个文件，最新：{destination}"))
        except Exception as exc:
            stats.failed += 1
            events.put(("log", f"复制失败：{source.path}，原因：{exc}"))

        now = time.monotonic()
        stats.elapsed_seconds = now - started_at
        stats.average_speed_bps = stats.processed_bytes / max(stats.elapsed_seconds, 0.001)
        stats.current_speed_bps = stats.average_speed_bps
        events.put(("progress", stats))

    if cancel_event.is_set():
        stats.cancelled = True

    stats.remaining_files = max(stats.total_files - stats.processed_files, 0)
    events.put(("done", stats))
    return stats

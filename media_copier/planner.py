from pathlib import Path

from .models import (
    ACTION_COPY,
    ACTION_COPY_RENAMED,
    ACTION_ERROR,
    ACTION_SKIP_DUPLICATE,
    ImportPlan,
    ImportPlanItem,
    ImportPlanSummary,
    SourceFile,
)
from .scanner import iter_matching_files
from .templates import build_target_path


def next_available_path(destination: Path, reserved_paths: set[Path]) -> Path:
    counter = 1
    while True:
        candidate = destination.with_name(f"{destination.stem}_{counter}{destination.suffix}")
        if candidate not in reserved_paths and not candidate.exists():
            return candidate
        counter += 1


def plan_item_for_source(
    source: SourceFile,
    target_dir: Path,
    template: str,
    reserved_paths: set[Path],
) -> ImportPlanItem:
    try:
        destination = build_target_path(source.path, target_dir, template)
        if destination in reserved_paths:
            renamed_destination = next_available_path(destination, reserved_paths)
            reserved_paths.add(renamed_destination)
            return ImportPlanItem(
                source=source,
                destination=renamed_destination,
                action=ACTION_COPY_RENAMED,
                original_destination=destination,
                reason="目标路径在本次导入计划中重复，已自动改名。",
            )

        if destination.exists():
            if destination.stat().st_size == source.size:
                return ImportPlanItem(
                    source=source,
                    destination=destination,
                    action=ACTION_SKIP_DUPLICATE,
                    reason="目标文件已存在且大小相同。",
                )

            renamed_destination = next_available_path(destination, reserved_paths)
            reserved_paths.add(renamed_destination)
            return ImportPlanItem(
                source=source,
                destination=renamed_destination,
                action=ACTION_COPY_RENAMED,
                original_destination=destination,
                reason="目标文件已存在但大小不同，已自动改名。",
            )

        reserved_paths.add(destination)
        return ImportPlanItem(source=source, destination=destination, action=ACTION_COPY)
    except Exception as exc:
        return ImportPlanItem(
            source=source,
            destination=target_dir,
            action=ACTION_ERROR,
            reason=str(exc),
        )


def summarize_plan(items: list[ImportPlanItem]) -> ImportPlanSummary:
    copy_actions = {ACTION_COPY, ACTION_COPY_RENAMED}
    return ImportPlanSummary(
        total_files=len(items),
        total_bytes=sum(item.source.size for item in items),
        copy_count=sum(1 for item in items if item.action in copy_actions),
        skip_count=sum(1 for item in items if item.action == ACTION_SKIP_DUPLICATE),
        renamed_count=sum(1 for item in items if item.action == ACTION_COPY_RENAMED),
        error_count=sum(1 for item in items if item.action == ACTION_ERROR),
        date_folder_count=len({item.destination.parent for item in items if item.action in copy_actions}),
    )


def build_import_plan(
    source_dir: Path,
    target_dir: Path,
    extensions: set[str] | None,
    template: str,
) -> ImportPlan:
    sources = iter_matching_files(source_dir, extensions)
    reserved_paths: set[Path] = set()
    items = [
        plan_item_for_source(source, target_dir, template, reserved_paths)
        for source in sources
    ]
    return ImportPlan(items=items, summary=summarize_plan(items))

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

RENAME_ACTION_RENAME = "rename"
RENAME_ACTION_SKIP = "skip"
RETRY_DELAYS = (0.2, 0.5, 1.0)
WINDOWS_RETRYABLE_ERRORS = {5, 32}


@dataclass(frozen=True)
class RenamePlanItem:
    source: Path
    destination: Path
    action: str
    item_type: str
    reason: str = ""


@dataclass(frozen=True)
class RenamePlanSummary:
    total_items: int = 0
    rename_count: int = 0
    skip_count: int = 0
    file_count: int = 0
    folder_count: int = 0


@dataclass(frozen=True)
class RenamePlan:
    items: list[RenamePlanItem]
    summary: RenamePlanSummary


@dataclass(frozen=True)
class RenameResult:
    renamed: int = 0
    skipped: int = 0
    failed: int = 0
    messages: tuple[str, ...] = ()


def natural_sort_key(path: Path) -> list[object]:
    parts = re.split(r"(\d+)", path.name.lower())
    return [int(part) if part.isdigit() else part for part in parts]


def summarize_rename_plan(items: list[RenamePlanItem]) -> RenamePlanSummary:
    return RenamePlanSummary(
        total_items=len(items),
        rename_count=sum(1 for item in items if item.action == RENAME_ACTION_RENAME),
        skip_count=sum(1 for item in items if item.action == RENAME_ACTION_SKIP),
        file_count=sum(1 for item in items if item.item_type == "file"),
        folder_count=sum(1 for item in items if item.item_type == "folder"),
    )


def candidate_paths(root: Path, recursive: bool) -> list[Path]:
    iterator = root.rglob("*") if recursive else root.iterdir()
    return sorted(iterator, key=lambda path: (len(path.parts), natural_sort_key(path)))


def make_plan_item(
    source: Path,
    destination: Path,
    planned_destinations: set[Path],
) -> RenamePlanItem:
    item_type = "folder" if source.is_dir() else "file"
    if source == destination:
        return RenamePlanItem(
            source=source,
            destination=destination,
            action=RENAME_ACTION_SKIP,
            item_type=item_type,
            reason="名称未变化。",
        )
    if destination.exists() or destination in planned_destinations:
        return RenamePlanItem(
            source=source,
            destination=destination,
            action=RENAME_ACTION_SKIP,
            item_type=item_type,
            reason="目标名称已存在或计划中重复，已跳过。",
        )
    planned_destinations.add(destination)
    return RenamePlanItem(
        source=source,
        destination=destination,
        action=RENAME_ACTION_RENAME,
        item_type=item_type,
    )


def build_replace_plan(
    root: Path,
    find_text: str,
    replace_text: str,
    include_files: bool,
    include_folders: bool,
    recursive: bool,
) -> RenamePlan:
    if not find_text:
        raise ValueError("查找内容不能为空。")
    if not include_files and not include_folders:
        raise ValueError("请至少选择文件或文件夹。")
    if not root.is_dir():
        raise ValueError("请选择有效的目标目录。")

    planned_destinations: set[Path] = set()
    items: list[RenamePlanItem] = []
    for path in candidate_paths(root, recursive):
        if path.is_file() and not include_files:
            continue
        if path.is_dir() and not include_folders:
            continue
        if find_text not in path.name:
            continue
        destination = path.with_name(path.name.replace(find_text, replace_text))
        items.append(make_plan_item(path, destination, planned_destinations))
    return RenamePlan(items=items, summary=summarize_rename_plan(items))


def build_sequence_plan(
    root: Path,
    prefix: str,
    start_number: int,
    digits: int,
) -> RenamePlan:
    if not root.is_dir():
        raise ValueError("请选择有效的目标目录。")
    if digits < 1:
        raise ValueError("编号位数必须大于 0。")
    if start_number < 0:
        raise ValueError("起始编号不能小于 0。")

    files = sorted([path for path in root.iterdir() if path.is_file()], key=natural_sort_key)
    planned_destinations: set[Path] = set()
    items: list[RenamePlanItem] = []
    for index, path in enumerate(files, start=start_number):
        destination = path.with_name(f"{prefix}{index:0{digits}d}{path.suffix}")
        items.append(make_plan_item(path, destination, planned_destinations))
    return RenamePlan(items=items, summary=summarize_rename_plan(items))


def executable_items(plan: RenamePlan) -> list[RenamePlanItem]:
    items = [item for item in plan.items if item.action == RENAME_ACTION_RENAME]
    files = [item for item in items if item.item_type == "file"]
    folders = [item for item in items if item.item_type == "folder"]
    folders.sort(key=lambda item: len(item.source.parts), reverse=True)
    return files + folders


def is_retryable_rename_error(exc: OSError) -> bool:
    return (
        isinstance(exc, PermissionError)
        or getattr(exc, "winerror", None) in WINDOWS_RETRYABLE_ERRORS
    )


def rename_with_retry(
    source: Path,
    destination: Path,
    sleep: Callable[[float], None] | None = None,
) -> None:
    sleep_func = sleep or time.sleep
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            source.rename(destination)
            return
        except OSError as exc:
            if not is_retryable_rename_error(exc) or attempt >= len(RETRY_DELAYS):
                raise
            sleep_func(RETRY_DELAYS[attempt])


def format_rename_error(exc: Exception) -> str:
    winerror = getattr(exc, "winerror", None)
    if winerror is not None:
        return f"Windows 错误 {winerror}：{exc}"
    return str(exc)


def execute_rename_plan(plan: RenamePlan) -> RenameResult:
    renamed = 0
    skipped = plan.summary.skip_count
    failed = 0
    messages: list[str] = []

    for item in executable_items(plan):
        try:
            if not item.source.exists():
                failed += 1
                messages.append(f"重命名失败：源项目不存在：{item.source}")
                continue
            if item.destination.exists():
                skipped += 1
                messages.append(f"跳过冲突：{item.destination}")
                continue
            rename_with_retry(item.source, item.destination)
            renamed += 1
            messages.append(f"已重命名：{item.source} -> {item.destination}")
        except Exception as exc:
            failed += 1
            messages.append(
                f"重命名失败：{item.source} -> {item.destination}，"
                f"原因：{format_rename_error(exc)}"
            )

    return RenameResult(
        renamed=renamed,
        skipped=skipped,
        failed=failed,
        messages=tuple(messages),
    )

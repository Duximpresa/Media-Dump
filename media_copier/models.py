from dataclasses import dataclass
from pathlib import Path

ACTION_COPY = "copy"
ACTION_COPY_RENAMED = "copy_renamed"
ACTION_SKIP_DUPLICATE = "skip_duplicate"
ACTION_ERROR = "error"


@dataclass(frozen=True)
class SourceFile:
    path: Path
    size: int


@dataclass(frozen=True)
class ImportPlanItem:
    source: SourceFile
    destination: Path
    action: str
    original_destination: Path | None = None
    reason: str = ""


@dataclass(frozen=True)
class ImportPlanSummary:
    total_files: int = 0
    total_bytes: int = 0
    copy_count: int = 0
    skip_count: int = 0
    renamed_count: int = 0
    error_count: int = 0
    date_folder_count: int = 0


@dataclass(frozen=True)
class ImportPlan:
    items: list[ImportPlanItem]
    summary: ImportPlanSummary


@dataclass
class CopyStats:
    total_files: int = 0
    total_bytes: int = 0
    processed_files: int = 0
    processed_bytes: int = 0
    copied: int = 0
    skipped: int = 0
    renamed: int = 0
    failed: int = 0
    verify_success: int = 0
    verify_failed: int = 0
    remaining_files: int = 0
    current_speed_bps: float = 0.0
    average_speed_bps: float = 0.0
    elapsed_seconds: float = 0.0
    cancelled: bool = False

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceFile:
    path: Path
    size: int


@dataclass
class CopyStats:
    total_files: int = 0
    total_bytes: int = 0
    processed_files: int = 0
    processed_bytes: int = 0
    copied: int = 0
    skipped: int = 0
    failed: int = 0
    remaining_files: int = 0
    current_speed_bps: float = 0.0
    average_speed_bps: float = 0.0
    elapsed_seconds: float = 0.0
    cancelled: bool = False


from pathlib import Path

from .models import SourceFile


def iter_matching_files(source_dir: Path, extensions: set[str] | None) -> list[SourceFile]:
    files = []
    for path in source_dir.rglob("*"):
        if not path.is_file():
            continue
        if extensions is not None and path.suffix.lower() not in extensions:
            continue
        files.append(SourceFile(path=path, size=path.stat().st_size))
    return files


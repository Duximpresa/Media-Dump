import os
from datetime import datetime
from pathlib import Path


def date_tokens(source_file: Path) -> dict[str, str]:
    created_at = datetime.fromtimestamp(os.path.getctime(source_file))
    return {
        "year": f"{created_at.year:04d}",
        "month": f"{created_at.month:02d}",
        "day": f"{created_at.day:02d}",
        "filename": source_file.name,
        "stem": source_file.stem,
        "ext": source_file.suffix,
    }


def build_target_path(source_file: Path, target_dir: Path, template: str) -> Path:
    return target_dir / Path(template.format(**date_tokens(source_file)))


def validate_template(template: str) -> None:
    tokens = {
        "year": "2026",
        "month": "05",
        "day": "26",
        "filename": "IMG_0001.JPG",
        "stem": "IMG_0001",
        "ext": ".JPG",
    }
    try:
        rendered = template.format(**tokens)
    except KeyError as exc:
        raise ValueError(f"模板变量不存在：{exc}") from exc
    except Exception as exc:
        raise ValueError(f"模板无法使用：{exc}") from exc
    if not rendered.strip():
        raise ValueError("模板渲染结果不能为空。")


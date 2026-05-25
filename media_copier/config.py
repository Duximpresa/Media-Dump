import json
import os
from pathlib import Path

from .constants import (
    APP_NAME,
    DEFAULT_TEMPLATE,
    OLD_DEFAULT_TEMPLATE,
    PHOTO_EXTENSIONS,
    VIDEO_EXTENSIONS,
)


def get_config_path() -> Path:
    base_dir = os.environ.get("APPDATA")
    if base_dir:
        return Path(base_dir) / APP_NAME / "config.json"
    return Path.home() / f".{APP_NAME}" / "config.json"


def default_config() -> dict:
    return {
        "source_dir": "",
        "target_dir": "",
        "selected_modes": ["photos", "videos"],
        "custom_extensions": ",".join(PHOTO_EXTENSIONS + VIDEO_EXTENSIONS),
        "date_template": DEFAULT_TEMPLATE,
        "duplicate_policy": "skip",
    }


def load_config() -> dict:
    config = default_config()
    config_path = get_config_path()
    if not config_path.exists():
        return config
    try:
        saved_config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return config
    if isinstance(saved_config, dict):
        config.update(saved_config)
    if config.get("date_template") == OLD_DEFAULT_TEMPLATE:
        config["date_template"] = DEFAULT_TEMPLATE
    return config


def save_config(config: dict) -> None:
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

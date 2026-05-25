from .constants import PHOTO_EXTENSIONS, VIDEO_EXTENSIONS


def normalize_extensions(raw_extensions: str) -> set[str]:
    extensions = set()
    for item in raw_extensions.replace(";", ",").split(","):
        ext = item.strip().lower()
        if not ext:
            continue
        if not ext.startswith("."):
            ext = f".{ext}"
        extensions.add(ext)
    return extensions


def selected_extensions(
    include_photos: bool,
    include_videos: bool,
    include_all: bool,
    include_custom: bool,
    custom_extensions: str,
) -> set[str] | None:
    if include_all:
        return None

    extensions = set()
    if include_photos:
        extensions.update(PHOTO_EXTENSIONS)
    if include_videos:
        extensions.update(VIDEO_EXTENSIONS)
    if include_custom:
        extensions.update(normalize_extensions(custom_extensions))
    return extensions


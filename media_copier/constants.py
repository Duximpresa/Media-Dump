APP_NAME = "MediaDateCopier"

OLD_DEFAULT_TEMPLATE = "{year}/{month}/{month}-{day}/{filename}"
DEFAULT_TEMPLATE = "{year}/{month}/{year}-{month}-{day}/{filename}"

PHOTO_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
    ".arw",
    ".cr2",
    ".cr3",
    ".nef",
    ".raf",
    ".dng",
    ".rw2",
    ".orf",
]

VIDEO_EXTENSIONS = [".mp4", ".mov", ".avi", ".mxf", ".mts", ".m2ts", ".insv"]

DATE_TEMPLATES = {
    "默认：2026/05/2026-05-26/文件名": DEFAULT_TEMPLATE,
    "年/月/日：2026/05/26/文件名": "{year}/{month}/{day}/{filename}",
    "日期文件夹：2026-05-26/文件名": "{year}-{month}-{day}/{filename}",
    "年/月-日：2026/05-26/文件名": "{year}/{month}-{day}/{filename}",
    "自定义": "",
}

CUSTOM_TEMPLATE_LABEL = "自定义"

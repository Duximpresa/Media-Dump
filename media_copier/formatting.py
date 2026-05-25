def format_bytes(size: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{value:.0f} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def format_speed(bytes_per_second: float) -> str:
    if bytes_per_second <= 0:
        return "0 B/s"
    return f"{format_bytes(bytes_per_second)}/s"


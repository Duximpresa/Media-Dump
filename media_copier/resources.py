import ctypes
import sys
from pathlib import Path
from tkinter import PhotoImage, TclError, Tk


def resource_path(relative_path: str) -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / relative_path
    return Path(__file__).resolve().parents[1] / relative_path


def configure_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Duximpresa.MediaDump"
        )
    except (AttributeError, OSError):
        pass


def configure_window_icon(root: Tk) -> None:
    icon_dir = Path("assets") / "icon"
    ico_path = resource_path(str(icon_dir / "mediadump-icon.ico"))
    png_path = resource_path(str(icon_dir / "mediadump-icon-1024.png"))

    try:
        if ico_path.is_file():
            root.iconbitmap(default=str(ico_path))
    except (OSError, TclError):
        pass

    try:
        if png_path.is_file():
            icon_image = PhotoImage(file=str(png_path))
            root.iconphoto(True, icon_image)
            root._mediadump_icon_image = icon_image
    except (OSError, TclError):
        pass

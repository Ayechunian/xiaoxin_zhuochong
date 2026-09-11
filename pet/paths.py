import os
import sys
from pathlib import Path


def resource_path(*parts):
    """Return a bundled read-only resource path or the source project path."""
    if getattr(sys, "frozen", False):
        root = Path(getattr(sys, "_MEIPASS"))
    else:
        root = Path(__file__).resolve().parent.parent
    return root.joinpath(*parts)


def user_data_dir():
    """Return a persistent writable folder, including for one-file builds."""
    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        root = Path(base) if base else Path.home()
        return root / "XiaoxinDesktopPet"
    return Path(__file__).resolve().parent.parent / "data"


def user_data_file(name):
    return user_data_dir() / name

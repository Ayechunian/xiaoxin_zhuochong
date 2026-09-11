"""Keep Qt and shiboken DLL directories active in frozen Windows builds."""

import builtins
import os
import sys


def _configure_dll_search_paths():
    if not getattr(sys, "frozen", False) or not hasattr(os, "add_dll_directory"):
        return

    bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    candidates = [
        os.path.join(bundle_dir, "PySide6"),
        os.path.join(bundle_dir, "shiboken6"),
        bundle_dir,
    ]
    handles = []
    path_entries = []
    for directory in candidates:
        if not os.path.isdir(directory):
            continue
        handles.append(os.add_dll_directory(directory))
        path_entries.append(directory)

    # Directory handles must stay alive for the lifetime of the application.
    builtins._xiaoxin_desktop_pet_dll_handles = handles
    if path_entries:
        os.environ["PATH"] = os.pathsep.join(path_entries + [os.environ.get("PATH", "")])


_configure_dll_search_paths()

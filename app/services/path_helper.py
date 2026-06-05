"""Path resolution helper — works in both dev and PyInstaller EXE."""

import os
import sys


def get_base_dir() -> str:
    """Get the project root directory.

    In development: returns the project root (parent directory of app/).
    In PyInstaller EXE: returns sys._MEIPASS (temporary extraction directory).
    """
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle
        return sys._MEIPASS
    # Running as normal Python script
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

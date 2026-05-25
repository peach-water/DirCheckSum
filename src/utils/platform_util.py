
import os
import platform
import subprocess

from src.utils.logger import getLogger

logger = getLogger(__name__)

def open_folder(path):
    """
    打开文件夹
    """
    system = platform.system()

    if system == "Windows":
        if hasattr(os, "startfile"):
            getattr(os, "startfile")(path)
        else:
            subprocess.Popen(["explorer", path])
    elif system == "Darwin": # macOS
        subprocess.Popen(["open", path])
    elif system == "Linux":
        subprocess.Popen(["xdg-open", path])
    else:
        try:
            subprocess.Popen(["xdg-open", path])
        except (OSError, subprocess.SubprocessError):
            logger.warning(f"cannot open folder on current system: {path}")
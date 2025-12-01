import os
import platform
from pathlib import Path
from datetime import datetime


def get_working_directory() -> str:
    return f"Working directory: {os.getcwd()}"


def check_git_repository() -> str:
    current_dir = Path(os.getcwd())
    
    for path in [current_dir] + list(current_dir.parents):
        git_dir = path / '.git'
        if git_dir.exists():
            return f"Is directory a git repo: Yes, In {path} git repository"
    
    return "Is directory a git repo: No"


def get_platform() -> str:
    return f"Platform: {platform.system().lower()}"


def get_os_version() -> str:
    return f"OS Version: {platform.platform()}"


def get_current_date() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return f"Today's date: {today}"


def get_environment_info() -> str:
    info_parts = [
        get_working_directory(),
        check_git_repository(),
        get_platform(),
        get_os_version(),
        get_current_date()
    ]
    return "\n".join(info_parts)
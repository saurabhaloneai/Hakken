import os
import platform
from pathlib import Path
from datetime import datetime

def get_working_directory():
    return f"Working directory: {os.getcwd()}"

def check_git_repository():
    current_dir = Path(os.getcwd())
    for path in [current_dir] + list(current_dir.parents):
        if (path / '.git').exists():
            return f"Is directory a git repo: Yes, In {path} git repository"
    return "Is directory a git repo: No"

def get_platform():
    return f"Platform: {platform.system().lower()}"

def get_os_version():
    return f"OS Version: {platform.platform()}"

def get_current_date():
    return f"Today's date: {datetime.now().strftime('%Y-%m-%d')}"

def get_environment_info():
    return "\n".join([
        get_working_directory(),
        check_git_repository(),
        get_platform(),
        get_os_version(),
        get_current_date()
    ])


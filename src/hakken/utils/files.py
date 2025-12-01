import os
from typing import Optional, Tuple


def validate_absolute_path(path: str) -> Optional[str]:
    if not path:
        return "Path is required"
    if not os.path.isabs(path):
        return f"Path must be absolute. Got: {path}"
    return None


def validate_file_exists(path: str) -> Optional[str]:
    if not os.path.exists(path):
        return f"File not found: {path}"
    if not os.path.isfile(path):
        return f"Path is not a file: {path}"
    return None


def read_file_lines(path: str, start: int = 1, end: Optional[int] = None) -> Tuple[str, list, int]:
    error = validate_absolute_path(path)
    if error:
        return error, [], 0
    
    error = validate_file_exists(path)
    if error:
        return error, [], 0
    
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    total = len(lines)
    
    if start < 1:
        start = 1
    if end is None or end > total:
        end = total
    
    if start > total:
        return f"Start line {start} exceeds file length {total}", [], total
    
    if start > end:
        return f"Start line {start} cannot exceed end line {end}", [], total
    
    return "", lines[start-1:end], total


def write_file_content(path: str, content: str, create_dirs: bool = True) -> Optional[str]:
    error = validate_absolute_path(path)
    if error:
        return error
    
    if create_dirs:
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return None


def replace_file_lines(path: str, content: str, start: int, end: Optional[int] = None) -> Optional[str]:
    error, lines, total = read_file_lines(path, 1, None)
    if error:
        return error
    
    if end is None:
        end = total
    
    if start > total + 1:
        return f"Start line {start} exceeds file length {total}"
    
    new_lines = content.splitlines(keepends=True)
    if content and not content.endswith('\n'):
        new_lines[-1] += '\n'
    
    if start > total:
        lines.extend(new_lines)
    else:
        lines[start-1:end] = new_lines
    
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return None


def ensure_directory(path: str) -> Optional[str]:
    error = validate_absolute_path(path)
    if error:
        return error
    
    os.makedirs(path, exist_ok=True)
    return None


def delete_file_or_dir(path: str) -> Optional[str]:
    error = validate_absolute_path(path)
    if error:
        return error
    
    if not os.path.exists(path):
        return f"Path not found: {path}"
    
    if os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        import shutil
        shutil.rmtree(path)
    
    return None

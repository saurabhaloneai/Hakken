import json
import os
from typing import Any, Optional, List


def read_json_file(path: str, default: Any = None) -> tuple[Optional[str], Any]:
    if not os.path.exists(path):
        return None, default if default is not None else []
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return None, data
    except json.JSONDecodeError as e:
        return f"Invalid JSON in {path}: {e}", default if default is not None else []
    except Exception as e:
        return f"Error reading {path}: {e}", default if default is not None else []


def write_json_file(path: str, data: Any, indent: int = 2) -> Optional[str]:
    try:
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return None
    except Exception as e:
        return f"Error writing to {path}: {e}"


def append_to_json_list(path: str, item: Any, max_items: Optional[int] = None) -> tuple[Optional[str], int]:
    error, data = read_json_file(path, [])
    if error:
        return error, 0
    
    if not isinstance(data, list):
        return f"{path} does not contain a JSON array", 0
    
    data.append(item)
    
    if max_items and len(data) > max_items:
        data = data[-max_items:]
    
    error = write_json_file(path, data)
    if error:
        return error, 0
    
    return None, len(data)


def update_json_dict(path: str, updates: dict) -> Optional[str]:
    error, data = read_json_file(path, {})
    if error:
        return error
    
    if not isinstance(data, dict):
        return f"{path} does not contain a JSON object"
    
    data.update(updates)
    return write_json_file(path, data)

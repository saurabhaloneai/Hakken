"""JSON parsing utilities."""
import json
from typing import Tuple, Optional


def is_valid_json_start(s: str) -> bool:
    """Check if string starts with valid JSON character."""
    idx = 0
    while idx < len(s):
        if s[idx] in ' \t\n\r':
            idx += 1
            continue
        return (
            s[idx] in '{["' or 
            s[idx:idx+4] in ('true', 'null') or 
            s[idx:idx+5] == 'false' or 
            s[idx].isdigit() or 
            s[idx] == '-'
        )
    return False


def parse_tool_arguments(raw_args: str) -> Tuple[dict, Optional[str]]:
    """Parse tool arguments from JSON string.
    
    Args:
        raw_args: Raw JSON string containing tool arguments
        
    Returns:
        Tuple of (parsed_dict, error_message)
        If parsing succeeds, error_message is None
        If parsing fails, parsed_dict is empty and error_message contains the error
    """
    if not raw_args:
        return {}, None
    
    if not is_valid_json_start(raw_args):
        return {}, f"Invalid JSON: {raw_args[:100]}"
    
    try:
        decoded = json.loads(raw_args)
        if isinstance(decoded, dict):
            return decoded, None
        return {}, "Expected JSON object"
    except json.JSONDecodeError as e:
        return {}, f"Invalid JSON: {str(e)}"

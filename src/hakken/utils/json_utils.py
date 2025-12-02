"""JSON parsing utilities."""
import json
from typing import Tuple, Optional, Any


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


def _try_parse_stringified_json(value: Any) -> Any:
    """Recursively parse values that might be stringified JSON.
    
    LLMs sometimes double-encode JSON, sending arrays/objects as strings.
    This function detects and parses such cases.
    """
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(('[', '{')):
            try:
                parsed = json.loads(stripped)
                return _try_parse_stringified_json(parsed)
            except json.JSONDecodeError:
                return value
        return value
    elif isinstance(value, dict):
        return {k: _try_parse_stringified_json(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_try_parse_stringified_json(item) for item in value]
    return value


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
            decoded = _try_parse_stringified_json(decoded)
            return decoded, None
        return {}, "Expected JSON object"
    except json.JSONDecodeError as e:
        return {}, f"Invalid JSON: {str(e)}"

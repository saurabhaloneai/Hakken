import pytest
from hakken.utils.json_utils import parse_tool_arguments, _try_parse_stringified_json


def test_parse_normal_json():
    """Test parsing normal JSON arguments."""
    raw = '{"name": "test", "value": 123}'
    result, error = parse_tool_arguments(raw)
    
    assert error is None
    assert result == {"name": "test", "value": 123}


def test_parse_nested_objects():
    """Test parsing nested JSON objects."""
    raw = '{"outer": {"inner": "value"}}'
    result, error = parse_tool_arguments(raw)
    
    assert error is None
    assert result == {"outer": {"inner": "value"}}


def test_parse_stringified_array():
    """Test parsing when LLM sends array as string (double-encoded)."""
    raw = '{"todos": "[{\\"id\\": \\"1\\", \\"content\\": \\"Task 1\\", \\"status\\": \\"pending\\"}]"}'
    result, error = parse_tool_arguments(raw)
    
    assert error is None
    assert isinstance(result["todos"], list)
    assert len(result["todos"]) == 1
    assert result["todos"][0]["id"] == "1"
    assert result["todos"][0]["content"] == "Task 1"


def test_parse_stringified_object():
    """Test parsing when LLM sends object as string (double-encoded)."""
    raw = '{"config": "{\\"key\\": \\"value\\"}"}'
    result, error = parse_tool_arguments(raw)
    
    assert error is None
    assert isinstance(result["config"], dict)
    assert result["config"]["key"] == "value"


def test_parse_mixed_normal_and_stringified():
    """Test parsing mix of normal and stringified values."""
    raw = '{"name": "test", "items": "[1, 2, 3]"}'
    result, error = parse_tool_arguments(raw)
    
    assert error is None
    assert result["name"] == "test"
    assert result["items"] == [1, 2, 3]


def test_parse_empty_args():
    """Test parsing empty arguments."""
    result, error = parse_tool_arguments("")
    
    assert error is None
    assert result == {}


def test_parse_invalid_json():
    """Test parsing invalid JSON returns error."""
    raw = 'not valid json'
    result, error = parse_tool_arguments(raw)
    
    assert error is not None
    assert "Invalid JSON" in error
    assert result == {}


def test_parse_non_object_json():
    """Test parsing non-object JSON returns error."""
    raw = '[1, 2, 3]'
    result, error = parse_tool_arguments(raw)
    
    assert error is not None
    assert "Expected JSON object" in error


def test_try_parse_leaves_normal_strings():
    """Test that normal strings are not modified."""
    result = _try_parse_stringified_json("hello world")
    assert result == "hello world"


def test_try_parse_invalid_json_string():
    """Test that invalid JSON-like strings are left as-is."""
    result = _try_parse_stringified_json("[not valid json")
    assert result == "[not valid json"

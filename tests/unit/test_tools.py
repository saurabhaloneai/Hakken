import pytest
from hakken.tools import manager

@pytest.fixture
def tool_manager():
    return manager.ToolManager()

def test_tool_manager_initialization(tool_manager):
    assert tool_manager is not None

def test_tool_manager_add_tool(tool_manager):
    tool_manager.add_tool("test_tool", "Test Tool Description")
    assert "test_tool" in tool_manager.tools

def test_tool_manager_remove_tool(tool_manager):
    tool_manager.add_tool("test_tool", "Test Tool Description")
    tool_manager.remove_tool("test_tool")
    assert "test_tool" not in tool_manager.tools

def test_tool_manager_list_tools(tool_manager):
    tool_manager.add_tool("test_tool_1", "Test Tool 1 Description")
    tool_manager.add_tool("test_tool_2", "Test Tool 2 Description")
    tools = tool_manager.list_tools()
    assert len(tools) == 2
    assert "test_tool_1" in tools
    assert "test_tool_2" in tools

def test_tool_manager_tool_description(tool_manager):
    tool_manager.add_tool("test_tool", "Test Tool Description")
    description = tool_manager.get_tool_description("test_tool")
    assert description == "Test Tool Description"
"""Tests for ToolRegistry and ToolInterface"""
import pytest
from unittest.mock import Mock, AsyncMock
from src.tools.tool_interface import ToolRegistry, ToolInterface


class MockTool(ToolInterface):
    """Mock tool for testing"""
    
    @staticmethod
    def get_tool_name():
        return "mock_tool"
    
    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": "mock_tool",
                "description": "A mock tool for testing"
            }
        }
    
    def get_status(self):
        return "ready"
    
    async def act(self, **kwargs):
        return {"result": "mock success", "args": kwargs}


class TestToolRegistry:
    
    @pytest.fixture
    def registry(self):
        return ToolRegistry()
    
    @pytest.fixture
    def mock_tool(self):
        return MockTool()
    
    def test_register_tool(self, registry, mock_tool):
        registry.register_tool(mock_tool)
        
        assert "mock_tool" in registry.tools
        assert registry.get_tool("mock_tool") == mock_tool
    
    def test_get_all_tools(self, registry, mock_tool):
        registry.register_tool(mock_tool)
        
        all_tools = registry.get_all_tools()
        assert len(all_tools) == 1
        assert "mock_tool" in all_tools
    
    def test_get_tools_description(self, registry, mock_tool):
        registry.register_tool(mock_tool)
        
        descriptions = registry.get_tools_description()
        assert len(descriptions) == 1
        assert descriptions[0]["type"] == "function"
    
    @pytest.mark.asyncio
    async def test_run_tool(self, registry, mock_tool):
        registry.register_tool(mock_tool)
        
        result = await registry.run_tool("mock_tool", test_arg="value")
        
        assert result["result"] == "mock success"
        assert result["args"]["test_arg"] == "value"
    
    @pytest.mark.asyncio
    async def test_run_nonexistent_tool(self, registry):
        result = await registry.run_tool("nonexistent_tool")
        
        assert result == "Tool not found"
    
    def test_get_tool_status(self, registry, mock_tool):
        registry.register_tool(mock_tool)
        
        status = registry.get_tool_status("mock_tool")
        assert status == "ready"
        
        # Test nonexistent tool
        status = registry.get_tool_status("nonexistent")
        assert status == "Tool not found"
    
    @pytest.mark.asyncio
    async def test_tool_error_handling(self, registry):
        # Create a tool that raises an exception
        error_tool = Mock(spec=ToolInterface)
        error_tool.get_tool_name.return_value = "error_tool"
        error_tool.act = AsyncMock(side_effect=Exception("Test error"))
        
        registry.register_tool(error_tool)
        
        result = await registry.run_tool("error_tool")
        
        assert "Error occurred while running tool" in result
        assert "Test error" in result

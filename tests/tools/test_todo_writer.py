"""Tests for TodoWriteManager"""
import pytest
from unittest.mock import Mock
from src.tools.todo_writer import TodoWriteManager


class TestTodoWriteManager:
    
    @pytest.fixture
    def mock_ui(self):
        ui = Mock()
        ui.update_todos = Mock()
        return ui
    
    @pytest.fixture
    def todo_writer(self, mock_ui):
        return TodoWriteManager(mock_ui)
    
    def test_tool_name(self, todo_writer):
        assert todo_writer.get_tool_name() == "todo_write"
    
    def test_json_schema(self, todo_writer):
        schema = todo_writer.json_schema()
        assert schema["type"] == "function"
        assert "todos" in schema["function"]["parameters"]["properties"]
        assert schema["function"]["parameters"]["properties"]["todos"]["type"] == "array"
    
    @pytest.mark.asyncio
    async def test_write_new_todos(self, todo_writer, mock_ui):
        todos = [
            {"id": "1", "content": "Test task 1", "status": "pending"},
            {"id": "2", "content": "Test task 2", "status": "in_progress"}
        ]
        
        result = await todo_writer.act(todos=todos)
        
        assert "Error:" not in result
        assert "Successfully updated" in result
        assert len(todo_writer.todos) == 2
    
    @pytest.mark.asyncio
    async def test_invalid_todo_structure(self, todo_writer):
        invalid_todos = [
            {"id": "1", "content": "Missing status"}
            # Missing required "status" field
        ]
        
        result = await todo_writer.act(todos=invalid_todos)
        
        assert "Error:" in result

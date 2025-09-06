"""Tests for FileEditor tool"""
import pytest
from src.tools.file_editor import FileEditor


class TestFileEditor:
    
    @pytest.fixture
    def file_editor(self):
        return FileEditor()
    
    def test_tool_name(self, file_editor):
        assert file_editor.get_tool_name() == "edit_file"
    
    def test_json_schema(self, file_editor):
        schema = file_editor.json_schema()
        assert schema["type"] == "function"
        assert "file_path" in schema["function"]["parameters"]["properties"]
        assert "old_text" in schema["function"]["parameters"]["properties"]
        assert "new_text" in schema["function"]["parameters"]["properties"]
    
    @pytest.mark.asyncio
    async def test_edit_existing_file(self, file_editor, temp_dir):
        # Create a test file
        test_file = temp_dir / "edit_test.txt"
        test_file.write_text("Hello world\nThis is a test")
        
        result = await file_editor.act(
            str(test_file), 
            "Hello world", 
            "Hello Python"
        )
        
        assert result["status"] == "success"
        assert "data" in result
        assert "message" in result["data"]
        assert "File edited successfully" in result["data"]["message"]
        
        # Verify the edit
        content = test_file.read_text()
        assert "Hello Python" in content
        assert "Hello world" not in content
    
    @pytest.mark.asyncio
    async def test_edit_nonexistent_file(self, file_editor):
        result = await file_editor.act(
            "nonexistent.txt", 
            "old", 
            "new"
        )
        
        assert result["status"] == "error"
        assert result["error"] is not None
        assert "File not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_edit_text_not_found(self, file_editor, temp_dir):
        # Create a test file
        test_file = temp_dir / "edit_test.txt"
        test_file.write_text("Hello world")
        
        result = await file_editor.act(
            str(test_file), 
            "nonexistent text", 
            "new text"
        )
        
        assert result["status"] == "error"
        assert result["error"] is not None
        assert "Text not found" in result["error"]

"""Tests for FileReader tool"""
import pytest
from src.tools.file_reader import FileReader


class TestFileReader:
    
    @pytest.fixture
    def file_reader(self):
        return FileReader()
    
    def test_tool_name(self, file_reader):
        assert file_reader.get_tool_name() == "read_file"
    
    def test_tool_status(self, file_reader):
        assert file_reader.get_status() == "ready"
    
    def test_json_schema(self, file_reader):
        schema = file_reader.json_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "read_file"
        assert "file_path" in schema["function"]["parameters"]["properties"]
    
    @pytest.mark.asyncio
    async def test_read_existing_file(self, file_reader, sample_file):
        result = await file_reader.act(str(sample_file))
        
        assert "content" in result
        assert "file_path" in result
        assert "total_lines" in result
        assert result["total_lines"] > 0
        assert "1|class TestClass:" in result["content"]
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, file_reader):
        result = await file_reader.act("nonexistent.txt")
        
        assert "error" in result
        assert "File not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_read_with_line_range(self, file_reader, sample_file):
        result = await file_reader.act(str(sample_file), start_line=1, end_line=2)
        
        assert "content" in result
        lines = result["content"].split('\n')
        assert len(lines) == 2
        assert "1|class TestClass:" in lines[0]
    
    @pytest.mark.asyncio
    async def test_read_with_start_line_only(self, file_reader, sample_file):
        result = await file_reader.act(str(sample_file), start_line=3)
        
        assert "content" in result
        assert "3|" in result["content"]

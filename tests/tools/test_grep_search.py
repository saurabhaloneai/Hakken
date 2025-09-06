"""Tests for GrepSearch tool"""
import pytest
from src.tools.grep_search import GrepSearch


class TestGrepSearch:
    
    @pytest.fixture
    def grep_search(self):
        return GrepSearch()
    
    def test_tool_name(self, grep_search):
        assert grep_search.get_tool_name() == "grep_search"
    
    def test_json_schema(self, grep_search):
        schema = grep_search.json_schema()
        assert schema["type"] == "function"
        assert "pattern" in schema["function"]["parameters"]["properties"]
        assert "path" in schema["function"]["parameters"]["properties"]
    
    @pytest.mark.asyncio
    async def test_search_in_file(self, grep_search, sample_file):
        result = await grep_search.act("class", str(sample_file))
        
        assert "error" not in result
        assert "results" in result
        assert len(result["results"]) > 0
        assert result["results"][0]["content"] == "class TestClass:"
    
    @pytest.mark.asyncio
    async def test_search_in_directory(self, grep_search, sample_project):
        result = await grep_search.act("class", str(sample_project), ".py")
        
        assert "error" not in result
        assert "results" in result
        assert result["total_matches"] > 0
        
        # Should find classes in the project
        found_files = [r["file"] for r in result["results"]]
        assert any("main.py" in f for f in found_files)
    
    @pytest.mark.asyncio
    async def test_search_no_matches(self, grep_search, sample_file):
        result = await grep_search.act("nonexistent_pattern", str(sample_file))
        
        assert "error" not in result
        assert "results" in result
        assert len(result["results"]) == 0
        assert result["total_matches"] == 0
    
    @pytest.mark.asyncio
    async def test_search_nonexistent_path(self, grep_search):
        result = await grep_search.act("test", "/nonexistent/path")
        
        assert "error" in result
        assert "does not exist" in result["error"]
    
    @pytest.mark.asyncio
    async def test_search_with_extension_filter(self, grep_search, sample_project):
        result = await grep_search.act("import", str(sample_project), ".py")
        
        assert "error" not in result
        assert "results" in result
        
        # All results should be from .py files
        for result_item in result["results"]:
            assert result_item["file"].endswith(".py")

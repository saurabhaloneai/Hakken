"""Tests for GitTools"""
import pytest
import subprocess
from src.tools.git_tools import GitTools


class TestGitTools:
    
    @pytest.fixture
    def git_tools(self):
        return GitTools()
    
    def test_tool_name(self, git_tools):
        assert git_tools.get_tool_name() == "git_tools"
    
    def test_json_schema(self, git_tools):
        schema = git_tools.json_schema()
        assert schema["type"] == "function"
        assert "command" in schema["function"]["parameters"]["properties"]
        assert "enum" in schema["function"]["parameters"]["properties"]["command"]
    
    @pytest.mark.asyncio
    async def test_git_status_in_git_repo(self, git_tools):
        # This test assumes we're in a git repo (Hakken project)
        result = await git_tools.act("status")
        
        # Should either succeed or fail gracefully
        if result["status"] == "success":
            assert "data" in result
            assert "output" in result["data"]
            assert "command" in result["data"]
            assert result["data"]["command"] == "git status"
        else:
            # If git fails, error should be descriptive
            assert result["error"] is not None
            assert "Git command failed" in result["error"] or "Git error" in result["error"] or "Not a git repository" in result["error"]
    
    @pytest.mark.asyncio
    async def test_git_log(self, git_tools):
        result = await git_tools.act("log")
        
        if result["status"] == "success":
            assert "data" in result
            assert "output" in result["data"]
            assert "command" in result["data"]
            assert result["data"]["command"] == "git log"
    
    @pytest.mark.asyncio
    async def test_git_diff(self, git_tools):
        result = await git_tools.act("diff")
        
        if result["status"] == "success":
            assert "data" in result
            assert "output" in result["data"]
            assert "command" in result["data"]
            assert result["data"]["command"] == "git diff"
    
    @pytest.mark.asyncio
    async def test_invalid_git_command(self, git_tools):
        result = await git_tools.act("invalid_command")
        
        assert result["status"] == "error"
        assert result["error"] is not None
        assert "Unknown git command" in result["error"]
    
    @pytest.mark.asyncio
    async def test_git_commands_enum(self, git_tools):
        """Test that only allowed commands are accepted"""
        valid_commands = ["status", "diff", "log"]
        
        for cmd in valid_commands:
            result = await git_tools.act(cmd)
            # Should not error due to invalid command
            if result["status"] == "error":
                assert result["error"] is not None
                assert "Unknown git command" not in result["error"]

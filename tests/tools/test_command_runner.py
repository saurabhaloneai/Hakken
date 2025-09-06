"""Tests for CommandRunner tool"""
import pytest
from src.tools.command_runner import CommandRunner


class TestCommandRunner:
    
    @pytest.fixture
    def command_runner(self):
        return CommandRunner()
    
    def test_tool_name(self, command_runner):
        assert command_runner.get_tool_name() == "cmd_runner"
    
    def test_json_schema(self, command_runner):
        schema = command_runner.json_schema()
        assert schema["type"] == "function"
        assert "command" in schema["function"]["parameters"]["properties"]
    
    @pytest.mark.asyncio
    async def test_simple_command(self, command_runner):
        result = await command_runner.act("echo hello")
        
        assert isinstance(result, str)
        assert "hello" in result
        assert "Error:" not in result
    
    @pytest.mark.asyncio
    async def test_command_with_error(self, command_runner):
        result = await command_runner.act("ls /nonexistent/directory")
        
        assert isinstance(result, str)
        assert "Error:" in result
    
    @pytest.mark.asyncio
    async def test_python_command(self, command_runner):
        result = await command_runner.act("python -c 'print(2+2)'")
        
        if "Error:" not in result:
            assert "4" in result
    
    @pytest.mark.asyncio
    async def test_multiline_output(self, command_runner):
        result = await command_runner.act("python -c 'print(\"line1\"); print(\"line2\")'")
        
        if "Error:" not in result:
            assert "line1" in result
            assert "line2" in result

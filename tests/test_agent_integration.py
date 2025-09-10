"""
Comprehensive Integration Test for Hakken Agent

This test simulates a real-world scenario where the agent:
1. Creates a todo list for a complex task
2. Uses multiple tools to complete the task
3. Manages memory and state
4. Demonstrates end-to-end functionality

The test scenario: "Create a simple Python calculator app with tests"
This covers file creation, code writing, testing, and documentation.
"""

import asyncio
import tempfile
import shutil
import os
from pathlib import Path
import pytest
from unittest.mock import Mock, patch, AsyncMock

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent.loop import ConversationAgent
from agent.state_manager import AgentConfiguration, APIConfig, HistoryConfig
from interface.user_interface import HakkenCodeUI
from tools.tool_manager import ToolManager


class MockUI(HakkenCodeUI):
    """Mock UI for testing that captures outputs and provides inputs"""
    
    def __init__(self):
        super().__init__()
        self.outputs = []
        self.inputs = []
        self.current_input_index = 0
        self.todos = []
        
    def add_input(self, input_text: str):
        """Add a mock user input"""
        self.inputs.append(input_text)
    
    def display_message(self, message: str, **kwargs):
        """Capture displayed messages"""
        self.outputs.append(message)
    
    def display_todos(self, todos):
        """Capture todo display"""
        self.todos = todos
        self.outputs.append(f"TODOS: {todos}")
    
    def update_todos(self, todos):
        """Update todos"""
        self.todos = todos
    
    async def get_user_input(self, prompt: str) -> str:
        """Return mock user input"""
        if self.current_input_index < len(self.inputs):
            input_text = self.inputs[self.current_input_index]
            self.current_input_index += 1
            return input_text
        return "exit"  # Default to exit if no more inputs
    
    def display_welcome_header(self):
        """Mock welcome header"""
        self.outputs.append("WELCOME_HEADER")


class TestAgentIntegration:
    """Comprehensive integration tests for the Hakken agent"""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing"""
        temp_dir = tempfile.mkdtemp()
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        yield temp_dir
        os.chdir(original_cwd)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_api_client(self):
        """Mock OpenAI API client"""
        with patch('client.openai_client.APIClient') as mock:
            # Mock a typical agent response with tool calls
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = "I'll help you create a Python calculator app. Let me start by creating a todo list."
            mock_response.choices[0].message.tool_calls = [
                Mock(
                    id="call_1",
                    function=Mock(
                        name="todo_write",
                        arguments='{"todos": [{"id": 1, "content": "Create calculator.py with basic operations", "status": "pending"}, {"id": 2, "content": "Write unit tests for calculator", "status": "pending"}, {"id": 3, "content": "Create README with usage instructions", "status": "pending"}]}'
                    )
                )
            ]
            
            mock.return_value.acreate_completion.return_value = mock_response
            yield mock
    
    @pytest.fixture
    def agent_config(self):
        """Create test agent configuration"""
        return AgentConfiguration(
            api_config=APIConfig(
                api_key="test-key",
                model="gpt-4",
                temperature=0.1
            ),
            history_config=HistoryConfig(
                max_tokens=8000,
                max_messages=50
            )
        )
    
    @pytest.mark.asyncio
    async def test_complete_calculator_task_workflow(self, temp_workspace, mock_api_client, agent_config):
        """
        Test the complete workflow of creating a calculator app.
        This tests the core functionality of the agent in a real-world scenario.
        """
        # Setup
        mock_ui = MockUI()
        
        # Create agent with mock configuration
        agent = ConversationAgent(config=agent_config)
        agent.ui_interface = mock_ui
        
        # Mock the API responses for different stages
        responses = [
            # Initial todo creation response
            self._create_mock_response(
                content="I'll create a todo list for the calculator project.",
                tool_calls=[{
                    "id": "call_1",
                    "function": {
                        "name": "todo_write",
                        "arguments": '{"todos": [{"id": 1, "content": "Create calculator.py with basic arithmetic operations (+, -, *, /)", "status": "pending"}, {"id": 2, "content": "Write comprehensive unit tests", "status": "pending"}, {"id": 3, "content": "Create README.md with usage instructions", "status": "pending"}, {"id": 4, "content": "Test the calculator functionality", "status": "pending"}]}'
                    }
                }]
            ),
            # File creation response
            self._create_mock_response(
                content="Now I'll create the calculator.py file with basic operations.",
                tool_calls=[{
                    "id": "call_2", 
                    "function": {
                        "name": "edit_file",
                        "arguments": '{"file_path": "calculator.py", "old_text": "", "new_text": "class Calculator:\\n    def add(self, a, b):\\n        return a + b\\n    \\n    def subtract(self, a, b):\\n        return a - b\\n    \\n    def multiply(self, a, b):\\n        return a * b\\n    \\n    def divide(self, a, b):\\n        if b == 0:\\n            raise ValueError(\\"Cannot divide by zero\\")\\n        return a / b\\n\\nif __name__ == \\"__main__\\":\\n    calc = Calculator()\\n    print(\\"Calculator created successfully!\\")\\n    print(f\\"2 + 3 = {calc.add(2, 3)}\\")\\n    print(f\\"10 - 4 = {calc.subtract(10, 4)}\\")\\n    print(f\\"5 * 6 = {calc.multiply(5, 6)}\\")\\n    print(f\\"15 / 3 = {calc.divide(15, 3)}\\")"}'
                    }
                }]
            ),
            # Test creation response  
            self._create_mock_response(
                content="Creating comprehensive unit tests for the calculator.",
                tool_calls=[{
                    "id": "call_3",
                    "function": {
                        "name": "edit_file", 
                        "arguments": '{"file_path": "test_calculator.py", "old_text": "", "new_text": "import unittest\\nfrom calculator import Calculator\\n\\nclass TestCalculator(unittest.TestCase):\\n    def setUp(self):\\n        self.calc = Calculator()\\n    \\n    def test_add(self):\\n        self.assertEqual(self.calc.add(2, 3), 5)\\n        self.assertEqual(self.calc.add(-1, 1), 0)\\n        self.assertEqual(self.calc.add(0, 0), 0)\\n    \\n    def test_subtract(self):\\n        self.assertEqual(self.calc.subtract(10, 4), 6)\\n        self.assertEqual(self.calc.subtract(5, 5), 0)\\n        self.assertEqual(self.calc.subtract(-2, -3), 1)\\n    \\n    def test_multiply(self):\\n        self.assertEqual(self.calc.multiply(3, 4), 12)\\n        self.assertEqual(self.calc.multiply(0, 5), 0)\\n        self.assertEqual(self.calc.multiply(-2, 3), -6)\\n    \\n    def test_divide(self):\\n        self.assertEqual(self.calc.divide(15, 3), 5)\\n        self.assertEqual(self.calc.divide(10, 2), 5)\\n        \\n    def test_divide_by_zero(self):\\n        with self.assertRaises(ValueError):\\n            self.calc.divide(10, 0)\\n\\nif __name__ == \\"__main__\\":\\n    unittest.main()"}'
                    }
                }]
            ),
            # Task completion response
            self._create_mock_response(
                content="Task completed successfully! Calculator app with tests created.",
                tool_calls=[]
            )
        ]
        
        # Mock the API client to return our staged responses
        agent.api_client.acreate_completion = AsyncMock(side_effect=responses)
        
        # Define the task
        task_prompt = """
        You are a Python development assistant. Create a complete calculator application with the following requirements:
        1. Basic arithmetic operations (add, subtract, multiply, divide)
        2. Proper error handling for division by zero
        3. Comprehensive unit tests
        4. Clean, readable code structure
        
        Follow your standard planning process and use appropriate tools.
        """
        
        user_request = "Create a simple Python calculator app with unit tests"
        
        # Execute the task
        result = await agent.start_task(task_prompt, user_request)
        
        # Verify the workflow executed correctly
        self._verify_agent_workflow(agent, mock_ui, temp_workspace)
        
        # Verify files were created (mocked)
        assert any("calculator.py" in str(output) for output in mock_ui.outputs)
        assert any("test_calculator.py" in str(output) for output in mock_ui.outputs)
        
        # Verify todos were created and managed
        assert len(mock_ui.todos) > 0
        assert any("calculator.py" in todo.get("content", "") for todo in mock_ui.todos)
        assert any("unit tests" in todo.get("content", "").lower() for todo in mock_ui.todos)
        
        print("✅ Complete calculator workflow test passed!")
    
    @pytest.mark.asyncio
    async def test_agent_tool_integration(self, temp_workspace, agent_config):
        """Test that all major tools can be used together in a workflow"""
        
        mock_ui = MockUI()
        agent = ConversationAgent(config=agent_config)
        agent.ui_interface = mock_ui
        
        # Test tool manager initialization
        tool_manager = agent.tool_registry
        assert tool_manager is not None
        
        # Verify all expected tools are available
        expected_tools = [
            "todo_write", "edit_file", "read_file", "cmd_runner", 
            "web_search", "task_memory", "grep_search", "git_tools",
            "task_delegator", "context_cropper"
        ]
        
        available_tools = list(tool_manager.get_all_tools().keys())
        for tool in expected_tools:
            assert tool in available_tools, f"Tool {tool} not found in available tools: {available_tools}"
        
        # Test tool execution (with mocking to avoid external dependencies)
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stdout = "Test output"
            mock_subprocess.return_value.stderr = ""
            
            result = await tool_manager.run_tool("cmd_runner", command="echo 'test'", need_user_approve=False)
            assert "Test output" in str(result) or "no return" in str(result).lower()
        
        print("✅ Tool integration test passed!")
    
    @pytest.mark.asyncio 
    async def test_agent_memory_and_state_management(self, temp_workspace, agent_config):
        """Test memory management and state persistence"""
        
        mock_ui = MockUI()
        agent = ConversationAgent(config=agent_config)
        agent.ui_interface = mock_ui
        
        # Test state manager
        state_manager = agent.loop.state_manager
        assert state_manager is not None
        assert state_manager.config is not None
        assert state_manager.state is not None
        
        # Test task state management
        initial_task_state = state_manager.state.is_in_task
        
        # Simulate starting a task
        state_manager.state.is_in_task = True
        assert state_manager.state.is_in_task == True
        
        # Simulate finishing a task
        state_manager.state.is_in_task = False
        assert state_manager.state.is_in_task == False
        
        # Test history management
        history_manager = agent.history_manager
        assert history_manager is not None
        
        # Test adding messages
        initial_message_count = len(history_manager.get_current_messages())
        history_manager.add_message({"role": "user", "content": "test message"})
        assert len(history_manager.get_current_messages()) == initial_message_count + 1
        
        print("✅ Memory and state management test passed!")
    
    @pytest.mark.asyncio
    async def test_agent_error_handling_and_recovery(self, temp_workspace, agent_config):
        """Test error handling and recovery mechanisms"""
        
        mock_ui = MockUI()
        agent = ConversationAgent(config=agent_config)
        agent.ui_interface = mock_ui
        
        tool_manager = agent.tool_registry
        
        # Test tool error handling
        result = await tool_manager.run_tool("nonexistent_tool", param="value")
        assert "Tool not found" in result
        
        # Test tool execution error handling  
        with patch.object(tool_manager.get_tool("read_file"), "act", side_effect=Exception("Test error")):
            result = await tool_manager.run_tool("read_file", file_path="nonexistent.txt")
            assert "Error occurred" in result and "Test error" in result
        
        # Test graceful handling of malformed tool calls
        result = await tool_manager.run_tool("todo_write", todos="invalid_format")
        assert "Error" in result or "wrong" in result
        
        print("✅ Error handling and recovery test passed!")
    
    def _create_mock_response(self, content: str, tool_calls: list = None):
        """Create a mock API response"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = content
        
        if tool_calls:
            mock_response.choices[0].message.tool_calls = []
            for call in tool_calls:
                mock_call = Mock()
                mock_call.id = call["id"]
                mock_call.function = Mock()
                mock_call.function.name = call["function"]["name"]
                mock_call.function.arguments = call["function"]["arguments"]
                mock_response.choices[0].message.tool_calls.append(mock_call)
        else:
            mock_response.choices[0].message.tool_calls = None
            
        return mock_response
    
    def _verify_agent_workflow(self, agent, mock_ui, temp_workspace):
        """Verify the agent workflow executed correctly"""
        
        # Check that the agent used the todo system
        assert any("todo" in str(output).lower() for output in mock_ui.outputs), \
            f"No todo-related outputs found in: {mock_ui.outputs}"
        
        # Check that file operations were attempted
        assert any("calculator" in str(output) for output in mock_ui.outputs), \
            f"No calculator-related outputs found in: {mock_ui.outputs}"
        
        # Check that the agent followed the planning process
        assert len(mock_ui.outputs) > 0, "No outputs captured from agent"
        
        # Verify tool calls were made
        assert agent.api_client.acreate_completion.called, "API client was not called"


# Additional utility test for running the agent manually
@pytest.mark.asyncio
async def test_manual_agent_interaction():
    """
    A test that demonstrates how to manually interact with the agent
    This can be used for debugging and understanding agent behavior
    """
    
    # Create a simple mock scenario
    mock_ui = MockUI()
    mock_ui.add_input("Create a hello world Python script")
    mock_ui.add_input("exit")
    
    config = AgentConfiguration(
        api_config=APIConfig(
            api_key="test-key", 
            model="gpt-4",
            temperature=0.1
        )
    )
    
    agent = ConversationAgent(config=config)
    agent.ui_interface = mock_ui
    
    # Mock API response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = "I'll create a hello world script for you."
    mock_response.choices[0].message.tool_calls = [
        Mock(
            id="call_1",
            function=Mock(
                name="edit_file",
                arguments='{"file_path": "hello.py", "old_text": "", "new_text": "print(\\"Hello, World!\\")\\nprint(\\"Welcome to Hakken!\\")"}' 
            )
        )
    ]
    
    agent.api_client.acreate_completion = AsyncMock(return_value=mock_response)
    
    # This would normally start an interactive session
    # For testing, we'll just verify the setup works
    assert agent.loop is not None
    assert agent.tool_registry is not None
    assert len(agent.tool_registry.get_all_tools()) > 0
    
    print("✅ Manual interaction test setup passed!")


if __name__ == "__main__":
    # Run the tests
    print("🚀 Starting Hakken Agent Integration Tests...")
    
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])

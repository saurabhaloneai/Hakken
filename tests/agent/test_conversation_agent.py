"""Tests for ConversationAgent"""
import pytest
from unittest.mock import Mock, patch
from src.agent.conversation_agent import ConversationAgent, AgentConfiguration


class TestConversationAgent:
    
    @pytest.fixture
    def mock_config(self):
        config = Mock(spec=AgentConfiguration)
        config.api_config = Mock()
        config.history_config = Mock()
        return config
    
    @patch('src.agent.conversation_agent.APIClient')
    @patch('src.agent.conversation_agent.HakkenCodeUI')
    @patch('src.agent.conversation_agent.ConversationHistoryManager')
    @patch('src.agent.conversation_agent.PromptManager')
    @patch('src.agent.conversation_agent.InterruptConfigManager')
    def test_agent_initialization(self, mock_interrupt, mock_prompt, mock_history, 
                                 mock_ui, mock_api, mock_config):
        """Test that ConversationAgent initializes properly"""
        agent = ConversationAgent(mock_config)
        
        assert agent.config == mock_config
        assert agent.tool_registry is not None
        assert agent._is_in_task == False
        
        # Check that all components are initialized
        mock_api.assert_called_once()
        mock_ui.assert_called_once()
        mock_history.assert_called_once()
        mock_prompt.assert_called_once()
        mock_interrupt.assert_called_once()
    
    @patch('src.agent.conversation_agent.APIClient')
    @patch('src.agent.conversation_agent.HakkenCodeUI')
    @patch('src.agent.conversation_agent.ConversationHistoryManager')
    @patch('src.agent.conversation_agent.PromptManager')
    @patch('src.agent.conversation_agent.InterruptConfigManager')
    def test_tool_registration(self, mock_interrupt, mock_prompt, mock_history, 
                              mock_ui, mock_api, mock_config):
        """Test that tools are properly registered"""
        agent = ConversationAgent(mock_config)
        
        # Check that tools are registered
        tools = agent.tool_registry.get_all_tools()
        
        # Should have all our tools
        expected_tools = {
            "cmd_runner", "todo_write", "smart_context_cropper",
            "delegate_task", "task_memory", "read_file",
            "grep_search", "git_status", "edit_file", "web_search"
        }
        
        assert len(tools) == len(expected_tools)
        for tool_name in expected_tools:
            assert tool_name in tools
    
    @patch('src.agent.conversation_agent.APIClient')
    @patch('src.agent.conversation_agent.HakkenCodeUI')
    @patch('src.agent.conversation_agent.ConversationHistoryManager')
    @patch('src.agent.conversation_agent.PromptManager')
    @patch('src.agent.conversation_agent.InterruptConfigManager')
    def test_message_management(self, mock_interrupt, mock_prompt, mock_history, 
                               mock_ui, mock_api, mock_config):
        """Test message management functionality"""
        mock_history_instance = Mock()
        mock_history.return_value = mock_history_instance
        mock_history_instance.get_current_messages.return_value = []
        
        agent = ConversationAgent(mock_config)
        
        # Test adding message
        test_message = {"role": "user", "content": "test"}
        agent.add_message(test_message)
        
        mock_history_instance.add_message.assert_called_once_with(test_message)
        
        # Test getting messages
        messages = agent.messages
        mock_history_instance.get_current_messages.assert_called()


class TestAgentConfiguration:
    
    @patch('src.agent.conversation_agent.APIConfiguration')
    @patch('src.agent.conversation_agent.HistoryConfiguration')
    def test_configuration_from_environment(self, mock_history_config, mock_api_config):
        """Test that configuration loads from environment"""
        config = AgentConfiguration()
        
        assert config.api_config is not None
        assert config.history_config is not None
        mock_api_config.from_environment.assert_called_once()
        mock_history_config.from_environment.assert_called_once()

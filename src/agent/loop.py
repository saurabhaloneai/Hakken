"""
main conversation loop orchestrator and ConversationAgent.
this file brings together all the refactored classes and manages the recursive conversation loop.
it also provides the ConversationAgent class for backward compatibility.
"""

import asyncio
import contextlib
import logging
import sys
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

from client.openai_client import APIClient
from history.conversation_history import ConversationHistoryManager
from interface.user_interface import HakkenCodeUI
from tools.tool_manager import ToolManager
from tools.human_interrupt import InterruptConfigManager
from prompt.prompt_manager import PromptManager

from agent.state_manager import StateManager, AgentConfiguration, ConversationState, AgentConfig, AgentState
from agent.response_handler import ResponseHandler, ResponseData, APIError, StreamingError
from agent.tool_executor import ToolExecutor, ToolExecutionEntry, ToolExecutionError
from agent.interrupt_manager import InterruptManager
from agent.message_processor import MessageProcessor


class ConversationLoop:
    
    
    def __init__(self, config: Optional[AgentConfiguration] = None):
        # Initialize state manager first
        self.state_manager = StateManager(config)
        
        # Initialize core components
        self.api_client = APIClient(self.state_manager.config.api_config)
        self.ui_interface = HakkenCodeUI()
        self.history_manager = ConversationHistoryManager(
            self.state_manager.config.history_config, 
            self.ui_interface
        )
        self.tool_registry = ToolManager(self.ui_interface, self.history_manager, self)
        self.prompt_manager = PromptManager(self.tool_registry)
        self.interrupt_config_manager = InterruptConfigManager()
        
        # Initialize specialized managers
        self.response_handler = ResponseHandler(
            self.api_client, self.ui_interface, self.history_manager, self.state_manager
        )
        self.tool_executor = ToolExecutor(
            self.ui_interface, self.tool_registry, self.interrupt_config_manager, self.state_manager, self.prompt_manager
        )
        self.interrupt_manager = InterruptManager(self.ui_interface, self.state_manager)
        self.message_processor = MessageProcessor(
            self.ui_interface, self.history_manager, self.state_manager, self.prompt_manager
        )
        
        self.logger = logging.getLogger(__name__)
    
    @property
    def messages(self):
        
        return self.history_manager.get_current_messages()
    
    async def start_conversation(self) -> None:
        
        try:
            await self._initialize_conversation()
            await self._main_conversation_loop()
        except (KeyboardInterrupt, asyncio.CancelledError):
            self.logger.info("conversation interrupted by user")
        finally:
            await self._cleanup_conversation()
    
    async def start_task(self, task_system_prompt: str, user_input: str) -> str:
        
        self.state_manager.state.is_in_task = True
        self.history_manager.start_new_chat()
        
        await self.message_processor.add_system_message(task_system_prompt)
        await self.message_processor.add_user_message(user_input)

        try:
            await self._process_message_cycle()
            return self.history_manager.finish_chat_get_response()
        finally:
            self.state_manager.state.is_in_task = False
    
    async def _initialize_conversation(self) -> None:
        self.ui_interface.display_welcome_header()
        system_prompt = self.prompt_manager.get_system_prompt()
        await self.message_processor.add_system_message(system_prompt)
    
    async def _main_conversation_loop(self) -> None:
        while True:
            user_input = await self.ui_interface.get_user_input(
                "What would you like me to help you with?"
            )
            await self.message_processor.add_user_message(user_input)
            await self._process_message_cycle()

    
    async def _process_message_cycle(self, show_thinking: bool = True) -> None:
        await self._prepare_request_cycle(show_thinking)
        response_data = await self.response_handler.get_assistant_response(
            self.response_handler.build_openai_request(self.tool_registry)
        )
        
        if response_data.early_exit:
            return
            
        await self._handle_response_data(response_data)
    
    async def _prepare_request_cycle(self, show_thinking: bool) -> None:
        self.history_manager.auto_messages_compression()
        
        if show_thinking:
            self.interrupt_manager.stop_spinner_safely()
            self.ui_interface.start_spinner("Thinking...")
            self.interrupt_manager.start_interrupt_flow()
    
    async def _handle_response_data(self, response_data) -> None:
        self.interrupt_manager.stop_interrupt_listener_safely()
        
        if response_data.token_usage:
            self.history_manager.update_token_usage(response_data.token_usage)

        self.message_processor.save_assistant_message(response_data)
        self.history_manager.auto_messages_compression()

        await self._execute_post_response_flow(response_data)
    
    async def _execute_post_response_flow(self, response_data) -> None:
        if response_data.interrupted:
            await self._process_message_cycle(show_thinking=True)
            return
        if self._has_tool_calls(response_data.message):
            await self.tool_executor.handle_tool_execution(response_data.message, self.history_manager)
            await self._process_message_cycle(show_thinking=True)
            return

        nudge_processed = await self.message_processor.check_for_action_nudges()
        if nudge_processed:
            await self._process_message_cycle(show_thinking=True)
            return
        
        pending_processed = await self.message_processor.handle_pending_instructions()
        if pending_processed:
            await self._process_message_cycle(show_thinking=True)
    
    async def _cleanup_conversation(self) -> None:
        with contextlib.suppress(Exception):
            await self.message_processor.maybe_prompt_and_save_on_exit(self.tool_registry)
        
        with contextlib.suppress(Exception):
            self.ui_interface.restore_session_terminal_mode()
        
        with contextlib.suppress(Exception):
            ctx = self.history_manager.current_context_window
            cost = self.api_client.total_cost
            self.ui_interface.display_exit_panel(ctx, str(cost))
    
    def _has_tool_calls(self, response_message) -> bool:
        return bool(hasattr(response_message, 'tool_calls') and response_message.tool_calls)


class ConversationAgent:
 
    
    def __init__(self, config: Optional[AgentConfiguration] = None):
        # Initialize the main loop orchestrator
        self.loop = ConversationLoop(config)
        
        # Expose properties for backward compatibility
        self.config = self.loop.state_manager.config
        self.agent_config = self.loop.state_manager.agent_config
        self.state = self.loop.state_manager.state
        self.api_client = self.loop.api_client
        self.ui_interface = self.loop.ui_interface
        self.history_manager = self.loop.history_manager
        self.tool_registry = self.loop.tool_registry
        self.prompt_manager = self.loop.prompt_manager
        self.interrupt_manager = self.loop.interrupt_config_manager
        self.logger = self.loop.logger

    @property
    def messages(self):
        return self.history_manager.get_current_messages()

    def add_message(self, message):
        self.history_manager.add_message(message)

    async def start_conversation(self) -> None:
        await self.loop.start_conversation()

    async def start_task(self, task_system_prompt: str, user_input: str) -> str:
        return await self.loop.start_task(task_system_prompt, user_input)


async def main():
    loop = ConversationLoop()
    await loop.start_conversation()


if __name__ == "__main__":
    asyncio.run(main())

__all__ = [
    'ConversationLoop',
    'ConversationAgent',
    'AgentConfiguration', 
    'ConversationState',
    'AgentConfig',
    'AgentState',
    'ResponseData',
    'ToolExecutionEntry',
    'APIError',
    'StreamingError', 
    'ToolExecutionError'
]

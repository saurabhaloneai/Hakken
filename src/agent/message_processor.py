import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

from interface.user_interface import HakkenCodeUI
from history.conversation_history import ConversationHistoryManager
from agent.state_manager import StateManager
from agent.response_handler import ResponseData
from prompt.prompt_manager import PromptManager


class MessageProcessor:

    
    def __init__(self, ui_interface: HakkenCodeUI, history_manager: ConversationHistoryManager, 
                 state_manager: StateManager, prompt_manager: PromptManager):
        self.ui_interface = ui_interface
        self.history_manager = history_manager
        self.state_manager = state_manager
        self.prompt_manager = prompt_manager
        self.logger = logging.getLogger(__name__)
    
    async def add_system_message(self, content: str) -> None:
        message = {
            "role": "system", 
            "content": [{"type": "text", "text": content}]
        }
        self.history_manager.add_message(message)
    
    async def add_user_message(self, content: str) -> None:
        """Add user message to conversation history."""
        message = {
            "role": "user", 
            "content": [{"type": "text", "text": content}]
        }
        self.history_manager.add_message(message)
    
    def save_assistant_message(self, response_data: ResponseData) -> None:
        if response_data.interrupted and not response_data.content.strip():
            return

        content_to_save = self._determine_content_to_save(response_data)
        assistant_message = {
            "role": "assistant",
            "content": content_to_save,
            "tool_calls": self._extract_tool_calls_safe(response_data.message)
        }
        self.history_manager.add_message(assistant_message)
    
    def _determine_content_to_save(self, response_data: ResponseData) -> str:
        if response_data.content.strip():
            return response_data.content
        elif hasattr(response_data.message, 'content'):
            return response_data.message.content
        else:
            return str(response_data.message)
    
    def _extract_tool_calls_safe(self, message: Any) -> Optional[List[Any]]:
        if hasattr(message, 'tool_calls') and message.tool_calls:
            return message.tool_calls
        return None
    
    async def check_for_action_nudges(self) -> bool:
        try:
            last_msg = self.history_manager.get_current_messages()[-1]
            last_content = last_msg.get("content", "") if isinstance(last_msg, dict) else ""
            nudge_text = self._derive_action_nudge(str(last_content))
            
            if nudge_text:
                await self.add_user_message(nudge_text)
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error checking action nudges: {e}")
            return False
    
    async def handle_pending_instructions(self) -> bool:
        pending_instruction = self.state_manager.state.pending_user_instruction.strip()
        if pending_instruction:
            self.state_manager.state.pending_user_instruction = ""
            await self.add_user_message(pending_instruction)
            return True
        return False
    
    def _derive_action_nudge(self, assistant_text: str) -> Optional[str]:
        text = assistant_text.lower()
        
        if not text or len(text) > self.state_manager.agent_config.MAX_TEXT_LENGTH:
            return None
        
        if self._is_generic_response(text):
            return None
        
        return self._check_specific_nudges(text)
    
    def _is_generic_response(self, text: str) -> bool:
        generic_phrases = [
            "i can help you with", "common use cases", "capabilities", 
            "i'm designed to", "i can work with"
        ]
        return any(phrase in text for phrase in generic_phrases)
    
    def _check_specific_nudges(self, text: str) -> Optional[str]:
        """Check for specific nudges in text."""
        if "check the todo.md" in text or "check todo.md" in text:
            return "use read_file to open 'todo.md' now, do not describe."
        
        if self._should_nudge_directory_listing(text):
            return "use cmd_runner with 'ls -la' now, do not describe."
        
        if "open" in text and ("file" in text or "." in text):
            return "use read_file to open the stated file now, do not describe."
        
        return None
    
    def _should_nudge_directory_listing(self, text: str) -> bool:
        has_listing_terms = any(term in text for term in ["ls", "list the ", "show the "])
        has_target_terms = any(term in text for term in ["directory", "files", "structure"])
        has_action_terms = any(term in text for term in ["i will", "i'll", "let me", "run ", "execute ", "here is the"])
        
        return has_listing_terms and has_target_terms and has_action_terms
    
    def add_tool_response(self, tool_call: Any, content: str, is_last_tool: bool = False) -> None:
        tool_content = [{"type": "text", "text": content}]
        
        if is_last_tool:
            reminder_content = self.prompt_manager.get_reminder()
            if reminder_content:
                tool_content.append({"type": "text", "text": reminder_content})
        
        tool_message = {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.function.name,
            "content": tool_content
        }
        self.history_manager.add_message(tool_message)
    
    async def save_task_memory_on_exit(self, tool_registry) -> None:
        try:
            context_data = self._collect_exit_context()
            await tool_registry.run_tool(
                "task_memory",
                action="save",
                description="session autosave on exit",
                context=context_data,
                progress={},
                decisions=[],
                files_changed=[],
                next_steps=[],
            )
            self.ui_interface.display_success("Session saved to task memory")
        except Exception as e:
            self.logger.error(f"Autosave failed: {e}")
            self.ui_interface.display_error(f"Autosave failed: {e}")
    
    def _collect_exit_context(self) -> str:
        try:
            last_text = self._get_last_message_text()
            env_summary = self._get_environment_summary()
            return f"last_message:\n{last_text}\n\n{env_summary}".strip()
        except Exception as e:
            self.logger.error(f"Failed to collect exit context: {e}")
            return "Failed to collect context"
    
    def _get_last_message_text(self) -> str:
        messages = self.history_manager.get_current_messages() or []
        
        for message in reversed(messages):
            text = message.get("content", "") if isinstance(message, dict) else getattr(message, "content", "")
            if isinstance(text, str) and text.strip():
                return self.state_manager.truncate_string(text.strip(), 400)
        
        return ""
    
    def _get_environment_summary(self) -> str:
        try:
            env = self.prompt_manager.environment_collector.collect_all()
            return f"cwd: {env.working_directory}\nplatform: {env.platform}"
        except Exception as e:
            self.logger.error(f"Failed to collect environment: {e}")
            return ""
    
    async def maybe_prompt_and_save_on_exit(self, tool_registry) -> None:
        prefs = self.state_manager.load_prefs()
        
        if prefs.get("exit_auto_save", False):
            await self.save_task_memory_on_exit(tool_registry)
            return

        try:
            result = await self.ui_interface.confirm_action(
                "Save this session to task memory before exit?"
            )
            await self._handle_save_decision(result, prefs, tool_registry)
        except Exception as e:
            self.logger.error(f"Save prompt failed: {e}")
    
    async def _handle_save_decision(self, result: Union[str, bool], prefs: Dict[str, Any], tool_registry) -> None:
        if isinstance(result, str):
            decision = result.strip().lower()
            if decision == "always":
                prefs["exit_auto_save"] = True
                self.state_manager.save_prefs(prefs)
                await self.save_task_memory_on_exit(tool_registry)
            elif decision == "yes":
                await self.save_task_memory_on_exit(tool_registry)
        elif bool(result):
            await self.save_task_memory_on_exit(tool_registry)

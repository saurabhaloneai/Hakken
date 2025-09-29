import json
import traceback
import asyncio
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, AsyncGenerator, Union, Tuple
from core.client import APIClient
from prompt.prompt_manager import PromptManager
from tools.tool_manager import ToolManager
from history.conversation_history import ConversationHistoryManager, HistoryConfiguration
from interface.user_interface import HakkenCodeUI


class AgentTaskException(Exception):
    pass


class AgentState(Enum):
    IDLE = "idle"
    INTERACTIVE = "interactive"
    IN_TASK = "in_task"
    ERROR = "error"


@dataclass
class AgentConfiguration:
    max_recursion_depth: int = 50
    enable_streaming: bool = True
    fallback_to_non_streaming: bool = True
    auto_compression: bool = True
    
    @classmethod
    def from_environment(cls) -> 'AgentConfiguration':
        import os
        return cls(
            max_recursion_depth=int(os.getenv('AGENT_MAX_RECURSION_DEPTH', 50)),
            enable_streaming=bool(os.getenv('AGENT_ENABLE_STREAMING', True)),
            fallback_to_non_streaming=bool(os.getenv('AGENT_FALLBACK_NON_STREAMING', True)),
            auto_compression=bool(os.getenv('AGENT_AUTO_COMPRESSION', True))
        )


class SimpleMessage:
    def __init__(self, content):
        self.content = content
        self.role = "assistant"
        self.tool_calls = None


class ErrorMessage:
    def __init__(self, error_msg):
        self.content = f"Sorry, I encountered a technical problem: {error_msg}"
        self.role = "assistant"
        self.tool_calls = None


class Agent:
   
    def __init__(self, config: Optional[AgentConfiguration] = None):
        self._config = config or AgentConfiguration.from_environment()
        self._api_client = APIClient()
        self._ui_manager = HakkenCodeUI()
        history_config = HistoryConfiguration.from_environment()
        self._history_manager = ConversationHistoryManager(history_config)
        self._prompt_manager = PromptManager()
        self._tool_manager = ToolManager(
            ui_interface=self._ui_manager,
            history_manager=self._history_manager,
            conversation_agent=self
        )
        
        # Replace boolean flag with proper state management
        self._state = AgentState.IDLE
        self._state_lock = asyncio.Lock()
        self._recursion_depth = 0

    @property
    def messages(self):
        return self._history_manager.get_current_messages()

    def add_message(self, message):
        self._history_manager.add_message(message)

    async def _set_state(self, new_state: AgentState):
        async with self._state_lock:
            self._state = new_state

    async def _get_state(self) -> AgentState:
        async with self._state_lock:
            return self._state

    async def start_agent(self):
        await self._set_state(AgentState.INTERACTIVE)
        
        system_message = self._create_message(
            "system", 
            self._prompt_manager.get_system_prompt()
        )
        self.add_message(system_message)
        
        user_input = await self._ui_manager.get_user_input()
        user_message = self._create_message("user", user_input)
        self.add_message(user_message)

        try:
            await self._recursive_message_handling()
        except Exception as e:
            await self._set_state(AgentState.ERROR)
            self._ui_manager.print_error(f"System error occurred: {e}")
            traceback.print_exc()
        finally:
            await self._set_state(AgentState.IDLE)

    async def start_task(self, task_system_prompt: str, user_input: str) -> str:
        await self._set_state(AgentState.IN_TASK)
        self._recursion_depth = 0
        self._history_manager.start_new_chat()
        
        system_message = self._create_message("system", task_system_prompt)
        self.add_message(system_message)
        
        user_message = self._create_message("user", user_input)
        self.add_message(user_message)

        try:
            await self._recursive_message_handling()
        except Exception as e:
            await self._set_state(AgentState.ERROR)
            self._ui_manager.print_error(f"System error occurred during running task: {e}")
            traceback.print_exc()
            raise AgentTaskException(f"Task failed: {e}")
        finally:
            result = self._history_manager.finish_chat_get_response()
            await self._set_state(AgentState.IDLE)
            return result

    async def _recursive_message_handling(self):
        if self._recursion_depth >= self._config.max_recursion_depth:
            self._ui_manager.print_error("Maximum conversation depth reached")
            return
        
        self._recursion_depth += 1
        
        if self._config.auto_compression:
            self._history_manager.auto_messages_compression()

        request = {
            "messages": self._get_messages_with_cache_mark(),
            "tools": self._tool_manager.get_tools_description(),
        }
        try:
            response_message, token_usage = await self._process_api_response(request)
            
        except Exception as e:
            await self._set_state(AgentState.ERROR)
            response_message = ErrorMessage(str(e))
            self._ui_manager.print_assistant_message(response_message.content)
            return
            
        if token_usage:
            self._history_manager.update_token_usage(token_usage)
        
        assistant_message = {
            "role": "assistant",
            "content": response_message.content,
            "tool_calls": response_message.tool_calls if hasattr(response_message, 'tool_calls') and response_message.tool_calls else None
        }
        self.add_message(assistant_message)
        
        if self._config.auto_compression:
            self._history_manager.auto_messages_compression()

        if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
            await self._handle_tool_calls(response_message.tool_calls)
            await self._recursive_message_handling()
        else:
            current_state = await self._get_state()
            if current_state == AgentState.IN_TASK:
                return
            
            user_input = await self._ui_manager.get_user_input()
            user_message = self._create_message("user", user_input)
            self.add_message(user_message)
            await self._recursive_message_handling()

    async def _process_api_response(self, request: Dict[str, Any]) -> Tuple[Any, Optional[Any]]:
        if self._config.enable_streaming:
            try:
                return await self._process_streaming_response(request)
            except Exception as e:
                if not self._config.fallback_to_non_streaming:
                    raise
                
                self._ui_manager.print_error(f"Streaming response processing error: {e}")
                self._ui_manager.print_info(f"Error type: {type(e).__name__}")
                self._ui_manager.print_info("Trying non-streaming mode...")
        
        return await self._process_non_streaming_response(request)

    async def _process_streaming_response(self, request: Dict[str, Any]) -> Tuple[Any, Optional[Any]]:
        stream_generator = self._api_client.get_completion_stream(request)
        
        if stream_generator is None:
            raise Exception("Stream generator is None - API client returned no response")
        
        try:
            iterator = iter(stream_generator)
        except TypeError:
            raise Exception(f"Stream generator is not iterable. Type: {type(stream_generator)}")
        
        response_message = None
        full_content = ""
        token_usage = None
        
        self._ui_manager.start_stream_display()
        
        try:
            for chunk in iterator:
                if isinstance(chunk, str):
                    full_content += chunk
                    self._ui_manager.print_streaming_content(chunk)
                elif hasattr(chunk, 'role') and chunk.role == 'assistant':
                    response_message = chunk
                    if hasattr(chunk, 'usage') and chunk.usage:
                        token_usage = chunk.usage
                    break
                elif hasattr(chunk, 'usage') and chunk.usage:
                    token_usage = chunk.usage
        finally:
            self._ui_manager.stop_stream_display()
        
        if response_message is None:
            response_message = SimpleMessage(full_content)
            
        return response_message, token_usage

    async def _process_non_streaming_response(self, request: Dict[str, Any]) -> Tuple[Any, Optional[Any]]:
        response_message, token_usage = self._api_client.get_completion(request)
        self._ui_manager.print_assistant_message(response_message.content)
        return response_message, token_usage

    def _get_messages_with_cache_mark(self):
        messages = self._history_manager.get_current_messages()
        if not messages:
            return messages
        
        last_message = messages[-1]
        if "content" in last_message and last_message["content"]:
            last_message["content"][-1]["cache_control"] = {"type": "ephemeral"}
        return messages

    async def _handle_tool_calls(self, tool_calls):
        for i, tool_call in enumerate(tool_calls):
            is_last_tool = (i == len(tool_calls) - 1)
            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as e:
                self._ui_manager.print_error(f"Tool parameter parsing failed: {e}")
                tool_response = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": [
                        {"type": "text", "text": "tool call failed due to JSONDecodeError"}
                    ]
                }
                self.add_message(tool_response)
                continue
            
            # Check if user approval is needed
            need_approval = args.get('need_user_approve', False)
            if need_approval:
                approval_content = f"Tool: {tool_call.function.name}, args: {args}"
                approved, user_content = await self._ui_manager.wait_for_user_approval(approval_content)
                if not approved:
                    self._add_tool_response(tool_call, f"user denied tool execution: {user_content}", is_last_tool)
                    continue

            await self._execute_tool(tool_call, args, is_last_tool)

    async def _execute_tool(self, tool_call, args, is_last_tool=False):
        tool_args = {k: v for k, v in args.items() if k != 'need_user_approve'}
        self._ui_manager.show_preparing_tool(tool_call.function.name, tool_args)
        
        try:
            tool_response = await self._tool_manager.run_tool(tool_call.function.name, **tool_args)
            self._ui_manager.show_tool_execution(
                tool_call.function.name, tool_args, success=True, result=str(tool_response)
            )
            self._add_tool_response(tool_call, json.dumps(tool_response), is_last_tool)
        except Exception as e:
            self._ui_manager.show_tool_execution(
                tool_call.function.name, tool_args, success=False, result=str(e)
            )
            self._add_tool_response(tool_call, f"tool call failed: {str(e)}", is_last_tool)

    def _add_tool_response(self, tool_call, content, is_last_tool=False):
        tool_content = [{"type": "text", "text": content}]
        
        if is_last_tool:
            reminder_content = self._prompt_manager.get_reminder()
            tool_content.append({"type": "text", "text": reminder_content})
        
        tool_message = {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.function.name,
            "content": tool_content
        }
        self.add_message(tool_message)

    def _create_message(self, role: str, text: str) -> dict:
        return {
            "role": role,
            "content": [
                {"type": "text", "text": text}
            ]
        }
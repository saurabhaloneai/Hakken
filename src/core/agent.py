import json
import traceback
from core.client import APIClient
from prompt.prompt_manager import PromptManager
from tools.tool_manager import ToolManager
from history.conversation_history import ConversationHistoryManager, HistoryConfiguration
from interface.user_interface import HakkenCodeUI


class AgentTaskException(Exception):
    """Custom exception for agent task failures."""
    pass


class SimpleMessage:
    """Simple message container for API responses."""
    def __init__(self, content):
        self.content = content
        self.role = "assistant"
        self.tool_calls = None


class ErrorMessage:
    """Error message container for failed operations."""
    def __init__(self, error_msg):
        self.content = f"Sorry, I encountered a technical problem: {error_msg}"
        self.role = "assistant"
        self.tool_calls = None


class Agent:
    """
    Main agent class that handles chat flow and tool interactions.
    Manages conversation state and coordinates between components.
    """
    
    def __init__(self):
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
        self._is_in_task = False
        self._recursion_depth = 0
        self._max_recursion_depth = 50

    @property
    def messages(self):
        return self._history_manager.get_current_messages()

    def add_message(self, message):
        self._history_manager.add_message(message)

    async def start_agent(self):
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
            self._ui_manager.print_error(f"System error occurred: {e}")
            traceback.print_exc()

    async def start_task(self, task_system_prompt: str, user_input: str) -> str:
        self._is_in_task = True
        self._recursion_depth = 0
        self._history_manager.start_new_chat()
        
        system_message = self._create_message("system", task_system_prompt)
        self.add_message(system_message)
        
        user_message = self._create_message("user", user_input)
        self.add_message(user_message)

        try:
            await self._recursive_message_handling()
        except Exception as e:
            self._ui_manager.print_error(f"System error occurred during running task: {e}")
            traceback.print_exc()
            raise AgentTaskException(f"Task failed: {e}")
        
        self._is_in_task = False
        return self._history_manager.finish_chat_get_response()

    async def _recursive_message_handling(self):
        # Prevent infinite recursion
        if self._recursion_depth >= self._max_recursion_depth:
            self._ui_manager.print_error("Maximum conversation depth reached")
            return
        
        self._recursion_depth += 1
        self._history_manager.auto_messages_compression()

        request = {
            "messages": self._get_messages_with_cache_mark(),
            "tools": self._tool_manager.get_tools_description(),
        }
        
        try:
            stream_generator = self._api_client.get_completion_stream(request)
            
            if stream_generator is None:
                raise Exception("Stream generator is None - API client returned no response")
            
            response_message = None
            full_content = ""
            token_usage = None
            
            try:
                iterator = iter(stream_generator)
            except TypeError:
                raise Exception(f"Stream generator is not iterable. Type: {type(stream_generator)}")
            
            self._ui_manager.start_stream_display()
            
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

            self._ui_manager.stop_stream_display()
            
            if response_message is None:
                response_message = SimpleMessage(full_content)
            
        except Exception as e:
            self._ui_manager.print_error(f"Streaming response processing error: {e}")
            self._ui_manager.print_info(f"Error type: {type(e).__name__}")
            
            try:
                self._ui_manager.print_info("Trying non-streaming mode...")
                response_message, token_usage = self._api_client.get_completion(request)
                self._ui_manager.print_assistant_message(response_message.content)
                
                if token_usage:
                    self._history_manager.update_token_usage(token_usage)
                    
            except Exception as fallback_error:
                self._ui_manager.print_error(f"Non-streaming mode also failed: {fallback_error}")
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
        
        self._history_manager.auto_messages_compression()

        if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
            await self._handle_tool_calls(response_message.tool_calls)
            await self._recursive_message_handling()
        else:
            if self._is_in_task:
                return
            user_input = await self._ui_manager.get_user_input()
            user_message = self._create_message("user", user_input)
            self.add_message(user_message)
            await self._recursive_message_handling()

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

            await self._execute_tool(tool_call, args, is_last_tool)

    async def _execute_tool(self, tool_call, args, is_last_tool=False):
        """Execute a tool call and handle the response."""
        self._ui_manager.show_preparing_tool(tool_call.function.name, args)
        
        try:
            tool_response = await self._tool_manager.run_tool(tool_call.function.name, **args)
            self._ui_manager.show_tool_execution(
                tool_call.function.name, args, success=True, result=str(tool_response)
            )
            self._add_tool_response(tool_call, json.dumps(tool_response), is_last_tool)
        except Exception as e:
            self._ui_manager.show_tool_execution(
                tool_call.function.name, args, success=False, result=str(e)
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

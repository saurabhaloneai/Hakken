import json
import sys
import traceback
import asyncio
import os
from pathlib import Path
from typing import Optional, Dict, List, Any
from client.openai_client import APIClient, APIConfiguration
from history.conversation_history import ConversationHistoryManager, HistoryConfiguration
from interface.user_interface import HakkenCodeUI
from tools.tool_interface import ToolRegistry
from tools.command_runner import CommandRunner
from tools.todo_writer import TodoWriteManager
from tools.context_cropper import ContextCropper
from tools.task_delegator import TaskDelegator
from tools.task_memory_tool import TaskMemoryTool
from tools.human_interrupt import InterruptConfigManager
from tools.file_reader import FileReader
from tools.grep_search import GrepSearch
from tools.git_tools import GitTools
from tools.file_editor import FileEditor
from prompt.prompt_manager import PromptManager
current_dir = Path(__file__).parent.parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))



class AgentConfiguration:
  
    def __init__(self):
        self.api_config = APIConfiguration.from_environment()
        self.history_config = HistoryConfiguration.from_environment()


class ConversationAgent:
    
    def __init__(self, config: Optional[AgentConfiguration] = None):
    
        self.config = config or AgentConfiguration()
        
        self.api_client = APIClient(self.config.api_config)
        self.ui_interface = HakkenCodeUI()
      
        self.history_manager = ConversationHistoryManager(
            self.config.history_config, 
            self.ui_interface
        )
        
        self.tool_registry = ToolRegistry()
        self._register_tools()

        self.prompt_manager = PromptManager(self.tool_registry)
        self.interrupt_manager = InterruptConfigManager()
      
        self._is_in_task = False
    
    def _register_tools(self):
        # Core tools
        cmd_runner = CommandRunner()
        self.tool_registry.register_tool(cmd_runner)
        
        todo_writer = TodoWriteManager(self.ui_interface)
        self.tool_registry.register_tool(todo_writer)

        context_cropper = ContextCropper(self.history_manager)
        self.tool_registry.register_tool(context_cropper)

        task_delegator = TaskDelegator(self.ui_interface, self)
        self.tool_registry.register_tool(task_delegator)

        task_memory = TaskMemoryTool()
        self.tool_registry.register_tool(task_memory)
        
        # New development tools
        file_reader = FileReader()
        self.tool_registry.register_tool(file_reader)
        
        grep_search = GrepSearch()
        self.tool_registry.register_tool(grep_search)
        
        git_tools = GitTools()
        self.tool_registry.register_tool(git_tools)
        
        file_editor = FileEditor()
        self.tool_registry.register_tool(file_editor)

    @property
    def messages(self) -> List[Dict]: return self.history_manager.get_current_messages()
    
    def add_message(self, message: Dict) -> None:
        self.history_manager.add_message(message)

    async def start_conversation(self) -> None:
        try:
            # Display welcome header with Rich formatting
            self.ui_interface.display_welcome_header()
            
            system_message = {
                "role": "system", 
                "content": [
                    {"type": "text", "text": self.prompt_manager.get_system_prompt()}
                ]
            }
            self.add_message(system_message)
            
            while True:
                # Use the new chat interface instead of regular input
                user_input = await self.ui_interface.get_user_input("What would you like me to help you with?")
                user_message = {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": user_input}
                    ]
                }
                self.add_message(user_message)
                
                
                await self._recursive_message_handling()
                
        except KeyboardInterrupt:
            self.ui_interface.console.print("\n● Conversation ended. Goodbye! 👋\n")
            return
        except Exception as e:
            self.ui_interface.display_error(f"System error occurred: {e}")
            traceback.print_exc()

    async def start_task(self, task_system_prompt: str, user_input: str) -> str:
        self._is_in_task = True
        self.history_manager.start_new_chat()
        
        system_message = {
            "role": "system", 
            "content": [
                {"type": "text", "text": task_system_prompt}
            ]
        }
        self.add_message(system_message)
        
        user_message = {
            "role": "user", 
            "content": [
                {"type": "text", "text": user_input}
            ]
        }
        self.add_message(user_message)

        try:
            await self._recursive_message_handling()
        except Exception as e:
            self.ui_interface.display_error(f"System error occurred during running task: {e}")
            traceback.print_exc()
            sys.exit(1)
        
        self._is_in_task = False
        return self.history_manager.finish_chat_get_response()

    async def _recursive_message_handling(self, show_thinking: bool = True) -> None:
        self.history_manager.auto_messages_compression()
        
        # Show animated spinner for initial calls, not recursive ones
        if show_thinking:
            self.ui_interface.start_spinner("Thinking...")
        
        def _estimate_tokens(obj: Any) -> int:
            try:
                serialized = json.dumps(obj, ensure_ascii=False)
            except Exception:
                try:
                    serialized = str(obj)
                except Exception:
                    serialized = ""
            # Approximate 1 token ≈ 4 characters
            return max(0, (len(serialized) + 3) // 4)

        # Build messages/tools first so we can estimate token usage
        messages = self._get_messages_with_cache_mark()
        tools_description = self.tool_registry.get_tools_description()

        # Defaults and env-configurable parameters
        user_requested_max_out = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "8192"))
        context_limit = int(os.getenv("OPENAI_CONTEXT_LIMIT", "131072"))
        buffer_tokens = int(os.getenv("OPENAI_OUTPUT_BUFFER_TOKENS", "1024"))

        estimated_input_tokens = _estimate_tokens(messages) + _estimate_tokens(tools_description)
        safe_output_cap = max(256, context_limit - estimated_input_tokens - buffer_tokens)
        max_output_tokens = max(256, min(user_requested_max_out, safe_output_cap))
        temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))

        request = {
            "messages": messages,
            "tools": tools_description,
            "max_tokens": max_output_tokens,
            "temperature": temperature,
            "tool_choice": "auto",
        }
        
        try:
            stream_generator = self.api_client.get_completion_stream(request)
            
            if stream_generator is None:
                raise Exception("Stream generator is None - API client returned no response")
            
            response_message = None
            full_content = ""
            token_usage = None
            
            # Prepare to stream content; keep spinner running until first chunk arrives
            self.ui_interface.start_assistant_response()
            spinner_stopped = False
            
            try:
                for chunk in stream_generator:
                    if not spinner_stopped:
                        # Stop spinner on first output
                        self.ui_interface.stop_spinner()
                        print()
                        spinner_stopped = True
                    if isinstance(chunk, str):
                        full_content += chunk
                        self.ui_interface.stream_content(chunk)
                    elif hasattr(chunk, 'role') and chunk.role == 'assistant':
                        response_message = chunk
                        if hasattr(chunk, 'usage') and chunk.usage:
                            token_usage = chunk.usage
                    elif hasattr(chunk, 'usage') and chunk.usage:
                        token_usage = chunk.usage
            except Exception as stream_error:
                self.ui_interface.display_error(f"Streaming error: {stream_error}")
                # Try to recover gracefully
                if full_content.strip():
                    response_message = self._create_simple_message(full_content)
            finally:
                # Ensure spinner is stopped if no chunks were emitted
                if not spinner_stopped:
                    self.ui_interface.stop_spinner()
                    print()
            
            self.ui_interface.finish_assistant_response()
            
            # Ensure we have a response message
            if response_message is None:
                if full_content.strip():
                    response_message = self._create_simple_message(full_content)
                else:
                    response_message = self._create_simple_message("I apologize, but I didn't receive a complete response.")
                    self.ui_interface.display_assistant_message(response_message.content)
            elif not full_content.strip():
                # If we have a response message but no streaming content, display it
                self.ui_interface.display_assistant_message(response_message.content)
            
        except Exception as e:
            self.ui_interface.stop_spinner()
            self.ui_interface.display_error(f"Response processing error: {e}")
            
            try:
                self.ui_interface.display_info("🔄 Retrying with non-streaming mode...")
                response_message, token_usage = self.api_client.get_completion(request)
                self.ui_interface.display_assistant_message(response_message.content)
                
                if token_usage:
                    self.history_manager.update_token_usage(token_usage)
                    
            except Exception as fallback_error:
                self.ui_interface.display_error(f"Non-streaming mode also failed: {fallback_error}")
                response_message = self._create_error_message(str(e))
                self.ui_interface.display_assistant_message(response_message.content)
                return

        if token_usage:
            self.history_manager.update_token_usage(token_usage)
        
        # Create assistant message for history - use streaming content if available
        content_to_save = full_content if full_content.strip() else (
            response_message.content if hasattr(response_message, 'content') else str(response_message)
        )
        assistant_message = {
            "role": "assistant",
            "content": content_to_save,
            "tool_calls": response_message.tool_calls if hasattr(response_message, 'tool_calls') and response_message.tool_calls else None
        }
        self.add_message(assistant_message)
        
        self.history_manager.auto_messages_compression()

        # Handle tool calls if present
        if hasattr(response_message, 'tool_calls') and response_message.tool_calls is not None and len(response_message.tool_calls) > 0:
            # Start spinner for tool execution if not already running
            if not hasattr(self.ui_interface, '_spinner_active') or not self.ui_interface._spinner_active:
                self.ui_interface.start_spinner("Processing...")
            
            await self._handle_tool_calls(response_message.tool_calls)
            # Continue the conversation after tool execution (without showing "Thinking..." again)
            await self._recursive_message_handling(show_thinking=False)
        else:
            # Show context and cost only once at the end of the conversation turn
            self._print_context_window_and_total_cost()

    def _print_context_window_and_total_cost(self) -> None:
        context_usage = self.history_manager.current_context_window
        total_cost = self.api_client.total_cost
        self.ui_interface.display_status(context_usage, str(total_cost))

    def _get_messages_with_cache_mark(self) -> List[Dict]:
        messages = self.history_manager.get_current_messages()
        if messages and "content" in messages[-1] and messages[-1]["content"]:
            messages[-1]["content"][-1]["cache_control"] = {"type": "ephemeral"}
        return messages

    async def _handle_tool_calls(self, tool_calls) -> None:
        for i, tool_call in enumerate(tool_calls):
            is_last_tool = (i == len(tool_calls) - 1)
            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as e:
                self.ui_interface.print_error(f"Tool parameter parsing failed: {e}")
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

            should_execute = True
            user_response = ""
            
            if self.interrupt_manager.requires_approval(tool_call.function.name, args):
                approval_content = f"Tool: {tool_call.function.name}, args: {args}"
                # Simplified approval for HakkenCodeUI
                should_execute = await self.ui_interface.confirm_action(approval_content)
                action = "accept" if should_execute else "ignore"
                modified_args = args
                response = ""
                
                if action == "accept":
                    should_execute = True
                    args = modified_args
                elif action == "respond":
                    should_execute = True
                    args = modified_args
                    user_response = response
                elif action == "ignore":
                    should_execute = False
                    user_response = response

            if should_execute:
                await self._execute_tool(tool_call, args, is_last_tool, user_response)
            else:
                self._add_tool_response(tool_call, f"Tool execution skipped: {user_response}", is_last_tool)

    async def _execute_tool(self, tool_call, args: Dict, is_last_tool: bool = False, user_response: str = "") -> None:
        tool_args = {k: v for k, v in args.items() if k != 'need_user_approve'}
        
        # Update spinner text to show tool execution
        if hasattr(self.ui_interface, '_spinner_active') and self.ui_interface._spinner_active:
            self.ui_interface.update_spinner_text(f"Running {tool_call.function.name}...")
        else:
            self.ui_interface.display_info(f"🔧 {tool_call.function.name}...")
        
        if user_response:
            tool_args['user_instructions'] = user_response
        
        try:
            tool_response = await self.tool_registry.run_tool(tool_call.function.name, **tool_args)
            
            # Update spinner to show completion or display success message
            if hasattr(self.ui_interface, '_spinner_active') and self.ui_interface._spinner_active:
                self.ui_interface.update_spinner_text(f"✓ {tool_call.function.name} completed")
                # Small delay to show the completion message
                await asyncio.sleep(0.3)
            else:
                self.ui_interface.display_success(f"{tool_call.function.name} completed successfully")
            response_content = json.dumps(tool_response)
            if user_response:
                response_content += f" (User instructions: {user_response})"
            self._add_tool_response(tool_call, response_content, is_last_tool)
        except Exception as e:
            # Update spinner to show error or display error message
            if hasattr(self.ui_interface, '_spinner_active') and self.ui_interface._spinner_active:
                self.ui_interface.update_spinner_text(f"✗ {tool_call.function.name} failed")
                # Small delay to show the error message
                await asyncio.sleep(0.3)
            else:
                self.ui_interface.display_error(f"{tool_call.function.name} failed: {str(e)}")
            self._add_tool_response(tool_call, f"tool call failed, fail reason: {str(e)}", is_last_tool)

    def _add_tool_response(self, tool_call, content: str, is_last_tool: bool = False) -> None:
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
        self.add_message(tool_message)

    def _create_simple_message(self, content: str):
        class SimpleMessage:
            def __init__(self, content):
                self.content = content
                self.role = "assistant"
                self.tool_calls = None
        
        return SimpleMessage(content)

    def _create_error_message(self, error_msg: str):
        class ErrorMessage:
            def __init__(self, error_msg):
                self.content = f"Sorry, I encountered a technical problem: {error_msg}"
                self.role = "assistant"
                self.tool_calls = None
        
        return ErrorMessage(error_msg)
    
    async def _handle_user_interrupt(self, user_input: str) -> None:
        interrupt_message = {
            "role": "user",
            "content": [
                {"type": "text", "text": f"[INTERRUPT] {user_input}"}
            ]
        }
        self.add_message(interrupt_message)
        
        if "stop" in user_input.lower():
            self.ui_interface.display_warning("Process will stop after current tool completes")
        elif "change" in user_input.lower() or "modify" in user_input.lower():
            self.ui_interface.display_info("Instruction received - will be processed")
        else:
            self.ui_interface.display_info("Input received - will be incorporated into the next response")

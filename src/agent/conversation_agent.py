import json
import sys
import traceback
from pathlib import Path
from typing import Optional, Dict, List, Any
from client.openai_client import APIClient, APIConfiguration
from history.conversation_history import ConversationHistoryManager, HistoryConfiguration
from interface.user_interface import UserInterface
from tools.tool_interface import ToolRegistry
from tools.command_runner import CommandRunner
from tools.todo_writer import TodoWriteManager
from tools.context_cropper import ContextCropper
from tools.task_delegator import TaskDelegator
from tools.task_memory_tool import TaskMemoryTool
from tools.human_interrupt import InterruptConfigManager
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
        self.ui_interface = UserInterface()
      
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

    @property
    def messages(self) -> List[Dict]: return self.history_manager.get_current_messages()
    
    def add_message(self, message: Dict) -> None:
        self.history_manager.add_message(message)

    async def start_conversation(self) -> None:
        try:
            system_message = {
                "role": "system", 
                "content": [
                    {"type": "text", "text": self.prompt_manager.get_system_prompt()}
                ]
            }
            self.add_message(system_message)
            
            while True:
                # Use the new chat interface instead of regular input
                user_input = await self.ui_interface.get_chat_input("What would you like me to help you with?")
                user_message = {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": user_input}
                    ]
                }
                self.add_message(user_message)
                
                self.ui_interface.start_interrupt_mode()
                self.ui_interface.add_interrupt_callback(self._handle_user_interrupt)
                
                await self._recursive_message_handling()
                
        except KeyboardInterrupt:
            self.ui_interface.stop_interrupt_mode()
            self.ui_interface.console.print("\n● Conversation ended. Goodbye! 👋\n")
            return
        except Exception as e:
            self.ui_interface.stop_interrupt_mode()
            self.ui_interface.print_error(f"System error occurred: {e}")
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
            self.ui_interface.print_error(f"System error occurred during running task: {e}")
            traceback.print_exc()
            sys.exit(1)
        
        self._is_in_task = False
        return self.history_manager.finish_chat_get_response()

    async def _recursive_message_handling(self) -> None:

        self.history_manager.auto_messages_compression()
        
        await self.ui_interface.check_for_interrupts()

        request = {
            "messages": self._get_messages_with_cache_mark(),
            "tools": self.tool_registry.get_tools_description(),
            "max_tokens": 64000,  
            "temperature": 0.7,  
        }
        
        try:
            stream_generator = self.api_client.get_completion_stream(request)
            
            if stream_generator is None:
                raise Exception("Stream generator is None - API client returned no response")
            
            response_message = None
            full_content = ""
            token_usage = None
            
            # Start streaming display (for real-time typing effect)
            self.ui_interface.start_stream_display()
            
            try:
                for chunk in stream_generator:
                    if isinstance(chunk, str):
                        full_content += chunk
                        self.ui_interface.print_streaming_content(chunk)
                    elif hasattr(chunk, 'role') and chunk.role == 'assistant':
                        response_message = chunk
                        if hasattr(chunk, 'usage') and chunk.usage:
                            token_usage = chunk.usage
                    elif hasattr(chunk, 'usage') and chunk.usage:
                        token_usage = chunk.usage
            except Exception as stream_error:
                self.ui_interface.print_error(f"Streaming error: {stream_error}")
            
            self.ui_interface.stop_stream_display()
            
            # After streaming is complete, just ensure we have a response message
            # The content was already displayed during streaming, so no need to display again
            if full_content.strip():
                print("\n")  # Clean line break after streaming
            
            if response_message is None:
                if full_content:
                    response_message = self._create_simple_message(full_content)
                else:
                    response_message = self._create_simple_message("I apologize, but I didn't receive a complete response.")
                    # Only display if we didn't get any streaming content
                    if not full_content.strip():
                        self.ui_interface.print_assistant_message(response_message.content, use_chat=True)
            elif not full_content:
                # Only display if we don't have streaming content
                self.ui_interface.print_assistant_message(response_message.content, use_chat=True)
            
        except Exception as e:
            self.ui_interface.print_error(f"Streaming response processing error: {e}")
            self.ui_interface.print_info(f"Error type: {type(e).__name__}")
            traceback.print_exc()
            
            try:
                self.ui_interface.print_info("Trying non-streaming mode...")
                response_message, token_usage = self.api_client.get_completion(request)
                self.ui_interface.print_assistant_message(response_message.content, use_chat=True)
                
                if token_usage:
                    self.history_manager.update_token_usage(token_usage)
                    
            except Exception as fallback_error:
                self.ui_interface.print_error(f"Non-streaming mode also failed: {fallback_error}")
                response_message = self._create_error_message(str(e))
                self.ui_interface.print_assistant_message(response_message.content, use_chat=True)
                return

        if token_usage:
            self.history_manager.update_token_usage(token_usage)
        
        assistant_message = {
            "role": "assistant",
            "content": response_message.content,
            "tool_calls": response_message.tool_calls if hasattr(response_message, 'tool_calls') and response_message.tool_calls else None
        }
        self.add_message(assistant_message)
        
        self.history_manager.auto_messages_compression()

        if hasattr(response_message, 'tool_calls') and response_message.tool_calls is not None and len(response_message.tool_calls) > 0:
            await self._handle_tool_calls(response_message.tool_calls)
            
            # Continue the conversation after tool execution
            # This applies to both task mode and regular conversation
            await self._recursive_message_handling()
        else:
            pass

        self._print_context_window_and_total_cost()

    def _print_context_window_and_total_cost(self) -> None:
        context_usage = self.history_manager.current_context_window
        total_cost = self.api_client.total_cost
        self.ui_interface.display_context_info(context_usage, str(total_cost))

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
                options = self.interrupt_manager.get_approval_options(tool_call.function.name)
                
                action, modified_args, response = await self.ui_interface.wait_for_enhanced_approval(
                    approval_content, tool_call.function.name, args, options
                )
                
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
        self.ui_interface.show_preparing_tool(tool_call.function.name, tool_args)
        
        await self.ui_interface.check_for_interrupts()
        
        if user_response:
            tool_args['user_instructions'] = user_response
        
        try:
            tool_response = await self.tool_registry.run_tool(tool_call.function.name, **tool_args)
            
            await self.ui_interface.check_for_interrupts()
            
            self.ui_interface.show_tool_execution(
                tool_call.function.name, 
                tool_args, 
                success=True, 
                result=str(tool_response)
            )
            response_content = json.dumps(tool_response)
            if user_response:
                response_content += f" (User instructions: {user_response})"
            self._add_tool_response(tool_call, response_content, is_last_tool)
        except Exception as e:
            self.ui_interface.show_tool_execution(
                tool_call.function.name, 
                tool_args, 
                success=False, 
                result=str(e)
            )
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
            self.ui_interface.print_warning("Process will stop after current tool completes")
        elif "change" in user_input.lower() or "modify" in user_input.lower():
            self.ui_interface.print_info("Instruction received - will be processed")
        else:
            self.ui_interface.print_info("Input received - will be incorporated into the next response")

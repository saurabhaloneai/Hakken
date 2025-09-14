import json
import asyncio
import contextlib
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass
from enum import Enum
from client.openai_client import APIClient, APIConfiguration
from interface.user_interface import HakkenCodeUI
from history.conversation_history import ConversationHistoryManager, HistoryConfiguration
from tools.tool_manager import ToolManager
from tools.human_interrupt import InterruptConfigManager
from prompt.prompt_manager import PromptManager

@dataclass
class ResponseData:
    message: Any
    content: str
    token_usage: Any
    interrupted: bool
    early_exit: bool = False

@dataclass
class Config:
    # All configuration in one place
    MAX_TEXT_LENGTH: int = 4000
    COMMAND_PREVIEW_MAX: int = 180
    ARGS_PREVIEW_MAX: int = 140
    INTERRUPT_TIMEOUT: float = 2.0
    STATUS_DELAY: float = 0.3
    MAX_CONTEXT_BUFFER: int = 1024
    DEFAULT_TEMPERATURE: float = 0.2
    DEFAULT_MAX_TOKENS: int = 8000
    DEFAULT_CONTEXT_LIMIT: int = 120000


class ConversationAgent:    
    def __init__(self, config: Optional[Dict] = None):
        self.config = Config()
        self.state = {
            'pending_instruction': '',
            'is_in_task': False,
            'tools_cache': None
        }
        self.api_client = APIClient(APIConfiguration.from_environment())
        self.ui = HakkenCodeUI()
        self.history = ConversationHistoryManager(HistoryConfiguration.from_environment(), self.ui)
        self.tools = ToolManager(self.ui, self.history, self)
        self.prompts = PromptManager(self.tools)
        self.interrupts = InterruptConfigManager()
        
        self.logger = logging.getLogger(__name__)
    
    # ============ PUBLIC API ============
    
    async def start_conversation(self) -> None:
        try:
            await self._setup_conversation()
            await self._conversation_loop()
        except (KeyboardInterrupt, asyncio.CancelledError):
            self.logger.info("Conversation interrupted by user")
        finally:
            await self._cleanup()
    
    async def start_task(self, system_prompt: str, user_input: str) -> str:
        self.state['is_in_task'] = True
        self.history.start_new_chat()
        
        await self._add_message("system", system_prompt)
        await self._add_message("user", user_input)
        
        try:
            await self._process_cycle()
            return self.history.finish_chat_get_response()
        finally:
            self.state['is_in_task'] = False
    
    @property
    def messages(self):
        return self.history.get_current_messages()
    
    # ============ CORE CONVERSATION FLOW ============
    
    async def _setup_conversation(self) -> None:
        self.ui.display_welcome_header()
        system_prompt = self.prompts.get_system_prompt()
        await self._add_message("system", system_prompt)
    
    async def _conversation_loop(self) -> None:
        """main conversation loop."""
        while True:
            user_input = await self.ui.get_user_input("What would you like me to help you with?")
            await self._add_message("user", user_input)
            await self._process_cycle()
    
    async def _process_cycle(self) -> None:
        """one complete request-response cycle."""
        # Prepare request
        self.history.auto_messages_compression()
        self._start_thinking()
        
        # Get llm response
        response = await self._get_ai_response()
        if response.early_exit:
            return
        
        # handle response
        self._stop_interrupts()
        self._save_response(response)

        if response.interrupted:
            await self._process_cycle()
        elif self._has_tools(response.message):
            await self._execute_tools(response.message)
            await self._process_cycle()
        elif await self._handle_nudges():
            await self._process_cycle()
        elif await self._handle_pending():
            await self._process_cycle()
    
    # ============ MESSAGE HANDLING ============
    
    async def _add_message(self, role: str, content: str) -> None:
        message = {
            "role": role,
            "content": [{"type": "text", "text": content}]
        }
        self.history.add_message(message)
    
    def _save_response(self, response: ResponseData) -> None:
        if response.interrupted and not response.content.strip():
            return
        content = response.content or getattr(response.message, 'content', str(response.message))
        message = {
            "role": "assistant",
            "content": content,
            "tool_calls": getattr(response.message, 'tool_calls', None)
        }
        self.history.add_message(message)
        if response.token_usage:
            self.history.update_token_usage(response.token_usage)
    
    # ============ LLM RESPONSE HANDLING ============ #
    
    async def _get_ai_response(self) -> ResponseData:
        request = self._build_request()
        
        try:
            return await self._stream_response(request)
        except Exception as e:
            self.logger.error(f"Streaming failed: {e}")
            return await self._fallback_response(request, e)
    
    def _build_request(self) -> Dict[str, Any]:
        messages = self._add_cache_markers(self.history.get_current_messages())
        tools = self.tools.get_tools_description()
        
        input_tokens = self._estimate_tokens(messages) + self._estimate_tokens(tools)
        max_tokens = self._compute_max_tokens(input_tokens)
        
        return {
            "messages": messages,
            "tools": tools,
            "max_tokens": max_tokens,
            "temperature": float(os.getenv("OPENAI_TEMPERATURE", self.config.DEFAULT_TEMPERATURE)),
            "tool_choice": "auto"
        }
    
    def _add_cache_markers(self, messages: List[Dict]) -> List[Dict]:
        if messages and messages[-1].get("content"):
            content = messages[-1]["content"]
            if isinstance(content, list) and content:
                content[-1]["cache_control"] = {"type": "ephemeral"}
        return messages
    
    async def _stream_response(self, request: Dict) -> ResponseData:
        stream = self.api_client.get_completion_stream(request)
        if not stream:
            raise Exception("No stream available")
        
        content_parts = []
        message = None
        usage = None
        interrupted = False
        
        self.ui.start_assistant_response()
        self._stop_spinner()
        
        try:
            if hasattr(stream, '__aiter__'):
                async for chunk in stream:
                    if self._process_chunk(chunk, content_parts, interrupted):
                        interrupted = True
                        break
                    if hasattr(chunk, 'role') and chunk.role == 'assistant':
                        message = chunk
                        if hasattr(chunk, 'usage'):
                            usage = chunk.usage
                    elif hasattr(chunk, 'usage'):
                        usage = chunk.usage
            else:
                for chunk in stream:
                    await asyncio.sleep(0)
                    if self._process_chunk(chunk, content_parts, interrupted):
                        interrupted = True
                        break
                    if hasattr(chunk, 'role') and chunk.role == 'assistant':
                        message = chunk
                        if hasattr(chunk, 'usage'):
                            usage = chunk.usage
                    elif hasattr(chunk, 'usage'):
                        usage = chunk.usage
        
        except Exception as e:
            self.ui.display_error(f"Streaming error: {e}")
            if content_parts:
                message = self._create_message(''.join(content_parts))
        finally:
            self.ui.finish_assistant_response()
        
        content = ''.join(content_parts)
        if not message and content:
            message = self._create_message(content)
        
        return ResponseData(message, content, usage, interrupted)
    
    def _process_chunk(self, chunk, content_parts: List[str], interrupted: bool) -> bool:
        if self._check_interrupt():
            return True
        if isinstance(chunk, str):
            content_parts.append(chunk)
            self.ui.stream_content(chunk)
        return False
    
    async def _fallback_response(self, request: Dict, error: Exception) -> ResponseData:
        self._stop_spinner()
        self.ui.display_info("Retrying without streaming...")
        try:
            message, usage = self.api_client.get_completion(request)
            self.ui.display_assistant_message(message.content)
            return ResponseData(message, message.content, usage, False)
        except Exception as e:
            error_msg = f"Sorry, I encountered a technical problem: {error}"
            self.ui.display_error(f"Fallback failed: {e}")
            return ResponseData(self._create_message(error_msg), error_msg, None, False, True)
    
    def _create_message(self, content: str) -> Any:
        class Message:
            def __init__(self, content):
                self.content = content
                self.role = "assistant"
                self.tool_calls = None
        return Message(content)
    
    # ============ TOOL EXECUTION ============
    
    async def _execute_tools(self, message: Any) -> None:
        if not hasattr(message, 'tool_calls'):
            return
        
        self._start_spinner("Processing...")
        pending = self.state.get('pending_instruction', '').strip()
        self.state['pending_instruction'] = ''
        tools = []
        for i, call in enumerate(message.tool_calls):
            try:
                args = json.loads(call.function.arguments)
                tools.append({
                    'index': i,
                    'call': call,
                    'name': call.function.name,
                    'args': args,
                    'approved': True
                })
            except json.JSONDecodeError as e:
                self.ui.display_error(f"Tool parsing failed: {e}")
                continue
        for tool in tools:
            if self.interrupts.requires_approval(tool['name'], tool['args']):
                tool['approved'] = await self._get_approval(tool)
                
        approved_tools = [t for t in tools if t['approved']]
        parallel_tools = [t for t in approved_tools if self._is_parallel_safe(t['name'])]
        sequential_tools = [t for t in approved_tools if not self._is_parallel_safe(t['name'])]
        
        for tool in tools:
            if not tool['approved']:
                self._add_tool_response(tool['call'], f"Skipped: {pending}", 
                                      tool['index'] == len(message.tool_calls) - 1)
        # Execute in parallel
        if parallel_tools:
            self.ui.update_spinner_text(f"Running {len(parallel_tools)} tools...")
            tasks = [self._run_tool(t, pending) for t in parallel_tools]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for tool, result in zip(parallel_tools, results):
                content = json.dumps(result) if not isinstance(result, Exception) else f"Failed: {result}"
                is_last = tool['index'] == len(message.tool_calls) - 1 and not sequential_tools
                self._add_tool_response(tool['call'], content, is_last)
        
        # Execute sequentially
        for tool in sequential_tools:
            await self._run_single_tool(tool, pending, 
                                       tool['index'] == len(message.tool_calls) - 1)
    
    async def _run_tool(self, tool: Dict, user_input: str) -> Any:
        args = {k: v for k, v in tool['args'].items() if k != 'need_user_approve'}
        if user_input:
            args['user_instructions'] = user_input
        return await self.tools.run_tool(tool['name'], **args)
    
    async def _run_single_tool(self, tool: Dict, user_input: str, is_last: bool) -> None:
        try:
            self.ui.update_spinner_text(f"Running {tool['name']}...")
            result = await self._run_tool(tool, user_input)
            
            self.ui.update_spinner_text(f"✓ {tool['name']} completed")
            await asyncio.sleep(self.config.STATUS_DELAY)
            
            content = json.dumps(result)
            if user_input:
                content += f" (User: {user_input})"
            
            self._add_tool_response(tool['call'], content, is_last)
            
        except Exception as e:
            self.ui.update_spinner_text(f"✗ {tool['name']} failed")
            await asyncio.sleep(self.config.STATUS_DELAY)
            self._add_tool_response(tool['call'], f"Failed: {e}", is_last)
    
    def _add_tool_response(self, tool_call: Any, content: str, is_last: bool) -> None:
        tool_content = [{"type": "text", "text": content}]
        
        if is_last:
            reminder = self.prompts.get_reminder()
            if reminder:
                tool_content.append({"type": "text", "text": reminder})
        
        message = {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.function.name,
            "content": tool_content
        }
        self.history.add_message(message)
    
    async def _get_approval(self, tool: Dict) -> bool:
        preview = f"Tool: {tool['name']}, args: {self._format_args(tool['args'])}"
        result = await self.ui.confirm_action(preview)
        
        if isinstance(result, str) and result.lower() == "always":
            self.interrupts.set_always_allow(tool['name'], tool['args'])
            return True
        
        return bool(result) or (isinstance(result, str) and result.lower() == "yes")
    
    def _format_args(self, args: Dict) -> Dict:
        preview = {}
        for k, v in args.items():
            if isinstance(v, str) and len(v) > self.config.ARGS_PREVIEW_MAX:
                preview[k] = v[:self.config.ARGS_PREVIEW_MAX] + "..."
            else:
                preview[k] = v
        return preview
    
    def _is_parallel_safe(self, tool_name: str) -> bool:
        safe_tools = {"read_file", "grep_search", "git_tools", "web_search"}
        return tool_name in safe_tools
    
    # ============ NUDGES AND PENDING INSTRUCTIONS ============
    
    async def _handle_nudges(self) -> bool:
        try:
            messages = self.history.get_current_messages()
            if not messages:
                return False
            
            last_msg = messages[-1]
            # Only process nudges from assistant messages, not user or tool messages
            if last_msg.get("role") != "assistant":
                return False
                
            last_content = str(last_msg.get("content", "")).lower()
            if len(last_content) > self.config.MAX_TEXT_LENGTH:
                return False
            
            completion_indicators = [
                "successfully created", "task completed", "perfect!", "great!",
                "✅", "✓", "created successfully", "finished", "done"
            ]
            if any(indicator in last_content for indicator in completion_indicators):
                return False
            
            if ("check todo.md" in last_content or "check the todo.md" in last_content) and \
               ("let me" in last_content or "i'll" in last_content or "i will" in last_content):
                await self._add_message("user", "use read_file to open 'todo.md' now")
                return True
            
            if "let me check" in last_content and "directory" in last_content and \
               ("ls" in last_content or "list" in last_content):
                await self._add_message("user", "use cmd_runner with 'ls -la' now")
                return True
            
            if ("let me open" in last_content or "i'll open" in last_content) and \
               "file" in last_content:
                await self._add_message("user", "use read_file to open the stated file now")
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Nudge handling failed: {e}")
            return False
    
    async def _handle_pending(self) -> bool:
        pending = self.state.get('pending_instruction', '').strip()
        if pending:
            self.state['pending_instruction'] = ''
            await self._add_message("user", pending)
            return True
        return False
    
    # ============ UTILITIES ============
    
    def _has_tools(self, message: Any) -> bool:
        return bool(hasattr(message, 'tool_calls') and message.tool_calls)
    
    def _start_thinking(self) -> None:
        self._stop_spinner()
        self.ui.start_spinner("Thinking...")
        self._start_interrupts()
    
    def _start_spinner(self, text: str) -> None:
        try:
            self.ui.start_spinner(text)
        except Exception as e:
            self.logger.debug(f"Failed to start spinner '{text}': {e}")
            # Fallback: show simple message
            try:
                self.ui.display_info(f"⚙️ {text}")
            except:
                pass
        self._start_interrupts()
    
    def _stop_spinner(self) -> None:
        try:
            # Check if spinner is actually running before stopping
            if hasattr(self.ui, '_spinner_active') and getattr(self.ui, '_spinner_active', False):
                self.ui.stop_spinner()
        except Exception as e:
            self.logger.debug(f"Failed to stop spinner: {e}")
            # Try alternative stop methods if they exist
            with contextlib.suppress(Exception):
                if hasattr(self.ui, 'stop_spinner_safe'):
                    self.ui.stop_spinner_safe()
            with contextlib.suppress(Exception):
                if hasattr(self.ui, '_spinner_active'):
                    self.ui._spinner_active = False
    
    def _start_interrupts(self) -> None:
        with contextlib.suppress(Exception):
            self.ui.display_interrupt_hint()
            self.ui.start_interrupt_listener()
    
    def _stop_interrupts(self) -> None:
        with contextlib.suppress(Exception):
            self.ui.stop_interrupt_listener()
    
    def _check_interrupt(self) -> bool:
        try:
            interrupt = self.ui.poll_interrupt()
            return interrupt and interrupt.strip() == "ESC"
        except:
            return False
    
    def _estimate_tokens(self, obj: Any) -> int:
        try:
            text = json.dumps(obj) if not isinstance(obj, str) else obj
            return len(text) // 4  # Rough estimation
        except:
            return len(str(obj)) // 4
    
    def _compute_max_tokens(self, input_tokens: int) -> int:
        context_limit = int(os.getenv("OPENAI_CONTEXT_LIMIT", self.config.DEFAULT_CONTEXT_LIMIT))
        max_output = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", self.config.DEFAULT_MAX_TOKENS))
        buffer = self.config.MAX_CONTEXT_BUFFER
        
        available = context_limit - input_tokens - buffer
        return max(256, min(max_output, available))
    
    # ============ CLEANUP ============
    
    async def _cleanup(self) -> None:
        try:
            prefs = self._load_prefs()
            if prefs.get("exit_auto_save", False):
                await self._save_session()
            else:
                result = await self.ui.confirm_action("Save session to task memory?")
                if result:
                    if isinstance(result, str) and result.lower() == "always":
                        prefs["exit_auto_save"] = True
                        self._save_prefs(prefs)
                    await self._save_session()
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
        
        # Restore terminal
        with contextlib.suppress(Exception):
            self.ui.restore_session_terminal_mode()
        
        # Show exit info
        with contextlib.suppress(Exception):
            ctx = self.history.current_context_window
            cost = self.api_client.total_cost
            self.ui.display_exit_panel(ctx, str(cost))
    
    async def _save_session(self) -> None:
        try:
            # Get last message and environment info
            messages = self.history.get_current_messages() or []
            last_text = ""
            for msg in reversed(messages):
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    last_text = content[:400]
                    break
            
            env = self.prompts.environment_collector.collect_all()
            context = f"last_message:\n{last_text}\n\ncwd: {env.working_directory}\nplatform: {env.platform}"
            
            await self.tools.run_tool(
                "task_memory",
                action="save",
                description="session autosave on exit",
                context=context,
                progress={},
                decisions=[],
                files_changed=[],
                next_steps=[]
            )
            self.ui.display_success("Session saved to task memory")
        except Exception as e:
            self.ui.display_error(f"Save failed: {e}")
    
    def _load_prefs(self) -> Dict[str, Any]:
        try:
            path = Path(".hakken/agent_prefs.json")
            return json.loads(path.read_text()) if path.exists() else {}
        except:
            return {}
    
    def _save_prefs(self, prefs: Dict[str, Any]) -> None:
        try:
            path = Path(".hakken")
            path.mkdir(exist_ok=True)
            (path / "agent_prefs.json").write_text(json.dumps(prefs, indent=2))
        except Exception as e:
            self.logger.error(f"Failed to save preferences: {e}")
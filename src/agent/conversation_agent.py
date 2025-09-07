import json
import sys
import traceback
import asyncio
import os
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

# ensure the project src directory is importable before other imports
_src_dir = Path(__file__).parent.parent.absolute()
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

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
from tools.web_search import WebSearch
from prompt.prompt_manager import PromptManager



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
        self._pending_user_instruction: str = ""
        
        # tool schema token estimation cache: (schema_hash, estimated_tokens)
        self._tools_schema_cache: Optional[Tuple[str, int]] = None
    
    def _register_tools(self) -> None:
       
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
        
        file_reader = FileReader()
        self.tool_registry.register_tool(file_reader)
        
        grep_search = GrepSearch()
        self.tool_registry.register_tool(grep_search)
        
        git_tools = GitTools()
        self.tool_registry.register_tool(git_tools)
        
        file_editor = FileEditor()
        self.tool_registry.register_tool(file_editor)
        
        web_search = WebSearch()
        self.tool_registry.register_tool(web_search)

    @property
    def messages(self) -> List[Dict]:
        return self.history_manager.get_current_messages()
    
    def add_message(self, message: Dict) -> None:
        self.history_manager.add_message(message)

    async def start_conversation(self) -> None:
        try:
            self.ui_interface.display_welcome_header()
            
            system_message = {
                "role": "system", 
                "content": [
                    {"type": "text", "text": self.prompt_manager.get_system_prompt()}
                ]
            }
            self.add_message(system_message)
            
            while True:
                user_input = await self.ui_interface.get_user_input("What would you like me to help you with?")
                user_message = {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": user_input}
                    ]
                }
                self.add_message(user_message)
                
                
                await self._recursive_message_handling()
                
        except KeyboardInterrupt: #to avoid traceback
            try:
                await self._maybe_prompt_and_save_on_exit()
            except Exception:
                pass
            try:
                ctx = self.history_manager.current_context_window
                cost = self.api_client.total_cost
                # Ensure terminal control-char echo is restored to clean up any ^C artifacts as we exit
                try:
                    self.ui_interface.restore_session_terminal_mode()
                except Exception:
                    pass
                self.ui_interface.display_exit_panel(ctx, str(cost))
            except Exception:
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
        self._begin_thinking_if_needed(show_thinking)
        request = self._build_openai_request()

        response_message, full_content, token_usage, interrupted, early_exit = await self._get_assistant_response(request)
        if early_exit:
            return

        self._stop_interrupt_listener_safely()

        if token_usage:
            self.history_manager.update_token_usage(token_usage)

        self._save_assistant_message(response_message, full_content, interrupted)
        
        self.history_manager.auto_messages_compression()

        await self._post_response_flow(response_message, full_content, interrupted)
        self._stop_interrupt_listener_safely()

    def _begin_thinking_if_needed(self, show_thinking: bool) -> None:
        if show_thinking:
            # ensure any previous spinner is stopped before starting a new one
            try:
                self.ui_interface.stop_spinner()
            except Exception:
                pass
            self.ui_interface.start_spinner("Thinking...")
            self._start_interrupt_flow()

    def _build_openai_request(self) -> Dict:
        messages = self._get_messages_with_cache_mark()
        tools_description = self.tool_registry.get_tools_description()
        limits = self._get_openai_env_limits()
        estimated_input_tokens = self._estimate_tokens(messages) + self._estimate_tools_tokens(tools_description)
        max_output_tokens = self._compute_max_output_tokens(estimated_input_tokens, limits)
        temperature = self._get_temperature()

        request = {
            "messages": messages,
            "tools": tools_description,
            "max_tokens": max_output_tokens,
            "temperature": temperature,
            "tool_choice": "auto",
        }
        return request

    async def _get_assistant_response(self, request: Dict) -> Tuple[Any, str, Any, bool, bool]:
        response_message = None
        full_content = ""
        token_usage = None
        interrupted = False
        early_exit = False

        try:
            stream_generator = self.api_client.get_completion_stream(request)
            if stream_generator is None:
                raise Exception("Stream generator is None - API client returned no response")
            self.ui_interface.start_assistant_response()
            spinner_stopped = False

            try:
                for chunk in stream_generator:
                    interrupt_text = self._safe_poll_interrupt()
                    if interrupt_text is not None:
                        stripped = interrupt_text.strip()
                        if stripped in ("ESC", "/"):
                            interrupted = True
                            spinner_stopped = self._ensure_spinner_stopped(spinner_stopped)
                            instr = self._capture_instruction_interactively()
                            if instr:
                                try:
                                    self.ui_interface.start_spinner("Applying instruction...")
                                except Exception:
                                    pass
                                await self._handle_user_interrupt(instr)
                            break
                        elif stripped.lower() == "/stop":
                            interrupted = True
                            spinner_stopped = self._ensure_spinner_stopped(spinner_stopped)
                            await self._handle_user_interrupt(interrupt_text)
                            break
                        else:
                            self._pending_user_instruction = stripped
                            try:
                                self.ui_interface.display_info("instruction queued; will apply after this step")
                            except Exception:
                                pass
                    if not spinner_stopped:
                        spinner_stopped = self._ensure_spinner_stopped(spinner_stopped)
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
                if full_content.strip():
                    response_message = self._create_simple_message(full_content)
            finally:
                if not spinner_stopped:
                    self.ui_interface.stop_spinner()
                    print()

            self.ui_interface.finish_assistant_response()

            # if the model is requesting tool calls, skip fallback/printing here;
            # the tool flow will handle it next.
            if response_message is not None and self._has_tool_calls(response_message):
                pass
            elif response_message is None:
                if full_content.strip():
                    response_message = self._create_simple_message(full_content)
                else:
                    # no streamed chunks and no final message
                    if not interrupted:
                        response_message = self._create_simple_message("sorry, i didn't receive a complete response.")
                        self.ui_interface.display_assistant_message(response_message.content)
                    else:
                        response_message = self._create_simple_message("")
            elif not full_content.strip():
                # no streamed chunks; if final message has content, show it, otherwise fallback to non-streaming
                final_content = getattr(response_message, 'content', '')
                if isinstance(final_content, str) and final_content.strip():
                    self.ui_interface.display_assistant_message(final_content)
                else:
                    if not interrupted:
                        try:
                            self.ui_interface.display_info("no streamed content; retrying without streaming…")
                            fallback_msg, fallback_usage = self.api_client.get_completion(request)
                            self.ui_interface.display_assistant_message(fallback_msg.content)
                            if fallback_usage:
                                token_usage = fallback_usage
                                self.history_manager.update_token_usage(token_usage)
                            response_message = fallback_msg
                        except Exception as fb_err:
                            self.ui_interface.display_error(f"non-streaming fallback failed: {fb_err}")
                            response_message = self._create_error_message(str(fb_err))
                            self.ui_interface.display_assistant_message(response_message.content)
                            early_exit = True
                    else:
                        response_message = self._create_simple_message("")

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
                early_exit = True

        return response_message, full_content, token_usage, interrupted, early_exit

    def _save_assistant_message(self, response_message: Any, full_content: str, interrupted: bool) -> None:
        if not (interrupted and not full_content.strip()):
            content_to_save = full_content if full_content.strip() else (
                response_message.content if hasattr(response_message, 'content') else str(response_message)
            )
            assistant_message = {
                "role": "assistant",
                "content": content_to_save,
                "tool_calls": response_message.tool_calls if hasattr(response_message, 'tool_calls') and response_message.tool_calls else None
            }
            self.add_message(assistant_message)

    async def _post_response_flow(self, response_message: Any, full_content: str, interrupted: bool) -> None:
        if interrupted:
            await self._recursive_message_handling(show_thinking=True)
            return
        if self._has_tool_calls(response_message):
            if not hasattr(self.ui_interface, '_spinner_active') or not self.ui_interface._spinner_active:
                self.ui_interface.start_spinner("Processing…")
                self._start_interrupt_flow()
            await self._handle_tool_calls(self._extract_tool_calls(response_message))
            # re-enable spinner for the post-tool assistant turn so streaming is visible
            await self._recursive_message_handling(show_thinking=True)
        else:
            self._print_context_window_and_total_cost()
            try:
                last_msg = self.history_manager.get_current_messages()[-1]
                last_content = last_msg.get("content", "") if isinstance(last_msg, dict) else ""
                nudge_text = self._derive_action_nudge(str(last_content))
                if nudge_text:
                    nudge_message = {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": nudge_text}
                        ]
                    }
                    self.add_message(nudge_message)
                    await self._recursive_message_handling(show_thinking=True)
                    return
            except Exception:
                pass
            pending_after = self._pending_user_instruction.strip() if isinstance(getattr(self, "_pending_user_instruction", ""), str) else ""
            if pending_after:
                self._pending_user_instruction = ""
                interrupt_message = {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": pending_after}
                    ]
                }
                self.add_message(interrupt_message)
                await self._recursive_message_handling(show_thinking=True)

    def _print_context_window_and_total_cost(self) -> None:
        # suppress inline context/cost status in the output
        return

    def _get_messages_with_cache_mark(self) -> List[Dict]:
        messages = self.history_manager.get_current_messages()
        if messages and "content" in messages[-1] and messages[-1]["content"]:
            content = messages[-1]["content"]
            # Only attach cache_control for list-based content entries
            if isinstance(content, list) and isinstance(content[-1], dict):
                content[-1]["cache_control"] = {"type": "ephemeral"}
        return messages

    def _start_interrupt_flow(self) -> None:
        try:
            self.ui_interface.display_interrupt_hint()
        except Exception:
            pass
        try:
            self.ui_interface.start_interrupt_listener()
        except Exception:
            pass

    def _stop_interrupt_listener_safely(self) -> None:
        try:
            self.ui_interface.stop_interrupt_listener()
        except Exception:
            pass

    def _safe_poll_interrupt(self) -> Optional[str]:
        try:
            return self.ui_interface.poll_interrupt()
        except Exception:
            return None

    def _ensure_spinner_stopped(self, spinner_stopped: bool) -> bool:
        if not spinner_stopped:
            self.ui_interface.stop_spinner()
            print()
            return True
        return spinner_stopped

    def _capture_instruction_interactively(self) -> Optional[str]:
        try:
            self.ui_interface.pause_stream_display()
            self.ui_interface.flush_interrupts()
            # silent capture; no banner
            instr = self.ui_interface.wait_for_interrupt(timeout=2.0)
            if not instr:
                try:
                    self.ui_interface.stop_interrupt_listener()
                except Exception:
                    pass
                instr = self.ui_interface.capture_instruction()
                try:
                    self.ui_interface.start_interrupt_listener()
                except Exception:
                    pass
            return instr
        finally:
            try:
                self.ui_interface.resume_stream_display()
            except Exception:
                pass

    def _estimate_tokens(self, obj: Any) -> int:
        try:
            serialized = json.dumps(obj, ensure_ascii=False)
        except Exception:
            try:
                serialized = str(obj)
            except Exception:
                serialized = ""
        return max(0, (len(serialized) + 3) // 4)

    def _estimate_tools_tokens(self, tools_description: List[Dict]) -> int:
        """Estimate tokens for tool schemas with caching since they rarely change"""
        try:
            # Create a hash of the tools description for cache key
            serialized = json.dumps(tools_description, sort_keys=True, ensure_ascii=False)
            tools_hash = hashlib.md5(serialized.encode()).hexdigest()
            
            # Check if we have a cached result
            if self._tools_schema_cache is not None:
                cached_hash, cached_tokens = self._tools_schema_cache
                if cached_hash == tools_hash:
                    return cached_tokens
            
            # Calculate tokens and cache the result
            estimated_tokens = self._estimate_tokens(tools_description)
            self._tools_schema_cache = (tools_hash, estimated_tokens)
            return estimated_tokens
            
        except Exception:
            # Fallback to direct estimation
            return self._estimate_tokens(tools_description)

    def _get_openai_env_limits(self) -> Dict[str, int]:
        return {
            "user_requested_max_out": int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "8192")),
            "context_limit": int(os.getenv("OPENAI_CONTEXT_LIMIT", "131072")),
            "buffer_tokens": int(os.getenv("OPENAI_OUTPUT_BUFFER_TOKENS", "1024")),
        }

    def _compute_max_output_tokens(self, estimated_input_tokens: int, limits: Dict[str, int]) -> int:
        safe_output_cap = max(256, limits["context_limit"] - estimated_input_tokens - limits["buffer_tokens"])
        return max(256, min(limits["user_requested_max_out"], safe_output_cap))

    def _get_temperature(self) -> float:
        return float(os.getenv("OPENAI_TEMPERATURE", "0.2"))

    def _has_tool_calls(self, response_message: Any) -> bool:
        return bool(hasattr(response_message, 'tool_calls') and response_message.tool_calls)

    def _extract_tool_calls(self, response_message: Any):
        return response_message.tool_calls if hasattr(response_message, 'tool_calls') and response_message.tool_calls else []

    async def _handle_tool_calls(self, tool_calls) -> None:
        # Capture any queued instruction to pass into the next tool execution
        pending_for_tools = self._pending_user_instruction.strip() if isinstance(getattr(self, "_pending_user_instruction", ""), str) else ""
        if pending_for_tools:
            # Clear the queue so it's not applied twice
            self._pending_user_instruction = ""

        # Parse arguments and collect entries
        entries = []
        for idx, tool_call in enumerate(tool_calls):
            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as e:
                self.ui_interface.print_error(f"Tool parameter parsing failed: {e}")
                # Record immediate failure response
                self._add_tool_response(
                    tool_call,
                    "tool call failed due to JSONDecodeError",
                    is_last_tool=(idx == len(tool_calls) - 1),
                )
                continue
            entries.append({
                "index": idx,
                "tool_call": tool_call,
                "name": tool_call.function.name,
                "args": args,
                "should_execute": True,
            })

        # Handle approvals sequentially to avoid overlapping interactive prompts
        for entry in entries:
            try:
                if self.interrupt_manager.requires_approval(entry["name"], entry["args"]):
                    approval_content = self._format_approval_preview(entry["name"], entry["args"])
                    approval_result = await self.ui_interface.confirm_action(approval_content)
                    if isinstance(approval_result, str):
                        decision = approval_result.strip().lower()
                        entry["should_execute"] = decision in ("yes", "always")
                        if decision == "always":
                            try:
                                self.interrupt_manager.set_always_allow(entry["name"], entry["args"])
                            except Exception:
                                pass
                    else:
                        entry["should_execute"] = bool(approval_result)
            except Exception:
                # On approval errors, skip execution conservatively
                entry["should_execute"] = False

        # Partition into parallel-safe and sequential entries
        parallel_safe_tools = {"read_file", "grep_search", "git_tools", "task_memory", "web_search"}

        def _is_parallel_safe(tool_name: str, args: dict) -> bool:
            if tool_name not in parallel_safe_tools:
                return False
            if tool_name == "task_memory":
                action = str(args.get("action", "")).strip().lower()
                return action in ("recall", "similar")
            # git_tools operations are read-only per implementation; others are fine
            return True

        parallel_entries = [e for e in entries if e["should_execute"] and _is_parallel_safe(e["name"], e["args"])]
        sequential_entries = [e for e in entries if e["should_execute"] and not _is_parallel_safe(e["name"], e["args"])]

        # Add skip responses for entries that should not execute
        skipped_indices = {e["index"] for e in entries if not e["should_execute"]}
        for idx in skipped_indices:
            tool_call = tool_calls[idx]
            self._add_tool_response(tool_call, f"Tool execution skipped: {pending_for_tools}", is_last_tool=(idx == len(tool_calls) - 1))

        # Determine which index is the last one overall for reminder placement
        last_index_overall = len(tool_calls) - 1 if tool_calls else -1

        # Execute parallel-safe entries concurrently
        async def _run_one(entry):
            tool_args = {k: v for k, v in entry["args"].items() if k != "need_user_approve"}
            if pending_for_tools:
                tool_args["user_instructions"] = pending_for_tools
            try:
                result = await self.tool_registry.run_tool(entry["name"], **tool_args)
                content = json.dumps(result)
            except Exception as e:
                content = f"tool call failed, fail reason: {str(e)}"
            return entry["index"], entry["tool_call"], content

        if parallel_entries:
            try:
                if hasattr(self.ui_interface, '_spinner_active') and self.ui_interface._spinner_active:
                    self.ui_interface.update_spinner_text(f"Running {len(parallel_entries)} tools in parallel…")
            except Exception:
                pass
            results = await asyncio.gather(*(_run_one(e) for e in parallel_entries))
            for idx, tool_call, content in sorted(results, key=lambda t: t[0]):
                self._add_tool_response(tool_call, content, is_last_tool=(idx == last_index_overall and not sequential_entries))

        # Execute remaining entries sequentially using existing pathway (preserves UI semantics)
        for e in sequential_entries:
            await self._execute_tool(
                e["tool_call"],
                e["args"],
                is_last_tool=(e["index"] == last_index_overall),
                user_response=pending_for_tools,
            )

    def _format_approval_preview(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Format a concise approval message with truncated/normalized args to avoid flooding the UI."""
        try:
            preview_args: Dict[str, Any] = {}
            if tool_name == "cmd_runner":
                cmd = args.get("command", "")
                if isinstance(cmd, str):
                    max_len = 180
                    normalized = cmd.replace("\n", " ")
                    if len(normalized) > max_len:
                        normalized = normalized[:max_len].rstrip() + "…"
                    preview_args["command"] = normalized
                    preview_args["length"] = len(cmd)
                else:
                    preview_args["command"] = str(cmd)
            else:
                # generic truncation for other tools
                for k, v in args.items():
                    if isinstance(v, str):
                        s = v.replace("\n", " ")
                        preview_args[k] = (s[:140].rstrip() + "…") if len(s) > 140 else s
                    else:
                        preview_args[k] = v
            return f"Tool: {tool_name}, args: {preview_args}"
        except Exception:
            return f"Tool: {tool_name}, args: {args}"

    def _derive_action_nudge(self, assistant_text: str) -> Optional[str]:
        text = assistant_text.lower()
        if not text or len(text) > 4000:
            return None
        # common intents → direct tool hints
        if "check the todo.md" in text or "check todo.md" in text:
            return "use read_file to open 'todo.md' now, do not describe."
        if "list" in text and ("directory" in text or "files" in text or "structure" in text):
            return "use cmd_runner with 'ls -la' now, do not describe."
        if "open" in text and ("file" in text or "." in text):
            return "use read_file to open the stated file now, do not describe."
        # disable web_search auto-nudge entirely to prevent loops
        return None

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
    
    # --- Exit-time memory save support ---
    def _get_prefs_path(self) -> Path:
        base = Path(os.getcwd()) / ".hakken"
        try:
            base.mkdir(exist_ok=True)
        except Exception:
            pass
        return base / "agent_prefs.json"

    def _load_prefs(self) -> dict:
        path = self._get_prefs_path()
        try:
            if path.exists():
                import json as _json
                return _json.loads(path.read_text(encoding="utf-8") or "{}")
        except Exception:
            pass
        return {}

    def _save_prefs(self, data: dict) -> None:
        path = self._get_prefs_path()
        try:
            import json as _json
            path.write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    async def _save_task_memory_on_exit(self) -> None:
        try:
            # Construct a concise context snapshot
            messages = self.history_manager.get_current_messages() or []
            last_text = ""
            for m in reversed(messages):
                text = m.get("content", "") if isinstance(m, dict) else getattr(m, "content", "")
                if isinstance(text, str) and text.strip():
                    last_text = text.strip()
                    break
            if last_text and len(last_text) > 400:
                last_text = last_text[:400].rstrip() + "…"

            try:
                env = self.prompt_manager.environment_collector.collect_all()
                env_summary = f"cwd: {env.working_directory}\nplatform: {env.platform}"
            except Exception:
                env_summary = ""

            description = "session autosave on exit"
            context = (f"last_message:\n{last_text}\n\n{env_summary}").strip()

            await self.tool_registry.run_tool(
                "task_memory",
                action="save",
                description=description,
                context=context,
                progress={},
                decisions=[],
                files_changed=[],
                next_steps=[],
            )
            try:
                self.ui_interface.display_success("session saved to task memory")
            except Exception:
                pass
        except Exception as e:
            try:
                self.ui_interface.display_error(f"autosave failed: {e}")
            except Exception:
                pass

    async def _maybe_prompt_and_save_on_exit(self) -> None:
        prefs = self._load_prefs()
        if bool(prefs.get("exit_auto_save", False)):
            await self._save_task_memory_on_exit()
            return

        try:
            result = await self.ui_interface.confirm_action("save this session to task memory before exit?")
        except Exception:
            result = False

        if isinstance(result, str):
            decision = result.strip().lower()
            if decision == "always":
                prefs["exit_auto_save"] = True
                self._save_prefs(prefs)
                await self._save_task_memory_on_exit()
                return
            if decision == "yes":
                await self._save_task_memory_on_exit()
                return
            return
        else:
            if bool(result):
                await self._save_task_memory_on_exit()
            return
    
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

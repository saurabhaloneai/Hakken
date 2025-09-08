import json
import sys
import asyncio
import os
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
import contextlib

sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

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
            system_message = {"role": "system", "content": [{"type": "text", "text": self.prompt_manager.get_system_prompt()}]}
            self.add_message(system_message)
            while True:
                user_input = await self.ui_interface.get_user_input("What would you like me to help you with?")
                user_message = {"role": "user", "content": [{"type": "text", "text": user_input}]}
                self.add_message(user_message)
                await self._recursive_message_handling()
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            with contextlib.suppress(Exception):
                await self._maybe_prompt_and_save_on_exit()
            with contextlib.suppress(Exception):
                self.ui_interface.restore_session_terminal_mode()
            with contextlib.suppress(Exception):
                ctx = self.history_manager.current_context_window
                cost = self.api_client.total_cost
                self.ui_interface.display_exit_panel(ctx, str(cost))

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
            return self.history_manager.finish_chat_get_response()
        finally:
            self._is_in_task = False

    async def _recursive_message_handling(self, show_thinking: bool = True) -> None:
        self.history_manager.auto_messages_compression()
        if show_thinking:
            with contextlib.suppress(Exception):
                self.ui_interface.stop_spinner()
            self.ui_interface.start_spinner("Thinking...")
            self._start_interrupt_flow()
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

    async def _consume_stream(self, stream_generator) -> Tuple[Any, str, Any, bool]:
        response_message = None
        full_content = ""
        token_usage = None
        interrupted = False
        self.ui_interface.start_assistant_response()
        spinner_stopped = False

        try:
            for chunk in stream_generator:
                interrupt_text = self._safe_poll_interrupt()
                if interrupt_text is not None:
                    stripped = interrupt_text.strip()
                    if stripped == "ESC":
                        interrupted = True
                        spinner_stopped = self._ensure_spinner_stopped(spinner_stopped)
                        instr = self._capture_instruction_interactively()
                        if instr:
                            with contextlib.suppress(Exception):
                                self.ui_interface.start_spinner("Applying instruction...")
                            self._pending_user_instruction = instr
                        break

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
            self.ui_interface.finish_assistant_response()

        return response_message, full_content, token_usage, interrupted

    def _finalize_stream_response(self, response_message: Any, full_content: str, token_usage: Any,
                                   interrupted: bool, request: Dict) -> Tuple[Any, Any, bool]:
        early_exit = False

        if response_message is not None and self._has_tool_calls(response_message):
            return response_message, token_usage, early_exit

        if response_message is None:
            if full_content.strip():
                response_message = self._create_simple_message(full_content)
            else:
                if not interrupted:
                    response_message = self._create_simple_message("sorry, i didn't receive a complete response.")
                    self.ui_interface.display_assistant_message(response_message.content)
                else:
                    response_message = self._create_simple_message("")
            return response_message, token_usage, early_exit

        if not full_content.strip():
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
                        response_message = self._create_simple_message(f"Sorry, I encountered a technical problem: {fb_err}")
                        self.ui_interface.display_assistant_message(response_message.content)
                        early_exit = True
                else:
                    response_message = self._create_simple_message("")

        return response_message, token_usage, early_exit

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

            response_message, full_content, token_usage, interrupted = await self._consume_stream(stream_generator)
            response_message, token_usage, early_exit = self._finalize_stream_response(
                response_message, full_content, token_usage, interrupted, request
            )

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
                response_message = self._create_simple_message(f"Sorry, I encountered a technical problem: {e}")
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
            await self._recursive_message_handling(show_thinking=True)
        else:
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

    def _get_messages_with_cache_mark(self) -> List[Dict]:
        messages = self.history_manager.get_current_messages()
        if messages and "content" in messages[-1] and messages[-1]["content"]:
            content = messages[-1]["content"]
            if isinstance(content, list) and isinstance(content[-1], dict):
                content[-1]["cache_control"] = {"type": "ephemeral"}
        return messages

    def _start_interrupt_flow(self) -> None:
        with contextlib.suppress(Exception):
            self.ui_interface.display_interrupt_hint()
        with contextlib.suppress(Exception):
            self.ui_interface.start_interrupt_listener()

    def _stop_interrupt_listener_safely(self) -> None:
        with contextlib.suppress(Exception):
            self.ui_interface.stop_interrupt_listener()

    def _safe_poll_interrupt(self) -> Optional[str]:
        try:
            return self.ui_interface.poll_interrupt()
        except Exception:
            return None

    def _ensure_spinner_stopped(self, spinner_stopped: bool) -> bool:
        if not spinner_stopped:
            self.ui_interface.stop_spinner()
            return True
        return spinner_stopped

    def _capture_instruction_interactively(self) -> Optional[str]:
        try:
            self.ui_interface.pause_stream_display()
            self.ui_interface.flush_interrupts()
            instr = self.ui_interface.wait_for_interrupt(timeout=2.0)
            if not instr:
                with contextlib.suppress(Exception):
                    self.ui_interface.stop_interrupt_listener()
                instr = self.ui_interface.capture_instruction()
                with contextlib.suppress(Exception):
                    self.ui_interface.start_interrupt_listener()
            return instr
        finally:
            with contextlib.suppress(Exception):
                self.ui_interface.resume_stream_display()

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
        try:
            serialized = json.dumps(tools_description, sort_keys=True, ensure_ascii=False)
            tools_hash = hashlib.md5(serialized.encode()).hexdigest()
            if self._tools_schema_cache is not None:
                cached_hash, cached_tokens = self._tools_schema_cache
                if cached_hash == tools_hash:
                    return cached_tokens
            estimated_tokens = self._estimate_tokens(tools_description)
            self._tools_schema_cache = (tools_hash, estimated_tokens)
            return estimated_tokens
        except Exception:
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
        pending_for_tools = self._extract_pending_instruction()
        entries = self._parse_tool_calls(tool_calls)
        await self._apply_approvals(entries)

        parallel_entries, sequential_entries = self._partition_parallel(entries)
        self._emit_skipped(tool_calls, entries, pending_for_tools)

        last_index_overall = len(tool_calls) - 1 if tool_calls else -1

        await self._run_parallel(parallel_entries, sequential_entries, last_index_overall, pending_for_tools)
        await self._run_sequential(sequential_entries, last_index_overall, pending_for_tools)

    def _extract_pending_instruction(self) -> str:
        pending_for_tools = self._pending_user_instruction.strip() if isinstance(getattr(self, "_pending_user_instruction", ""), str) else ""
        if pending_for_tools:
            self._pending_user_instruction = ""
        return pending_for_tools

    def _parse_tool_calls(self, tool_calls) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        for idx, tool_call in enumerate(tool_calls):
            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as e:
                with contextlib.suppress(Exception):
                    self.ui_interface.display_error(f"Tool parameter parsing failed: {e}")
                self._add_tool_response(tool_call, "tool call failed due to JSONDecodeError", is_last_tool=(idx == len(tool_calls) - 1))
                continue
            entries.append({
                "index": idx,
                "tool_call": tool_call,
                "name": tool_call.function.name,
                "args": args,
                "should_execute": True,
            })
        return entries

    async def _apply_approvals(self, entries: List[Dict[str, Any]]) -> None:
        for entry in entries:
            try:
                if self.interrupt_manager.requires_approval(entry["name"], entry["args"]):
                    approval_content = self._format_approval_preview(entry["name"], entry["args"])
                    approval_result = await self.ui_interface.confirm_action(approval_content)
                    if isinstance(approval_result, str):
                        decision = approval_result.strip().lower()
                        entry["should_execute"] = decision in ("yes", "always")
                        if decision == "always":
                            with contextlib.suppress(Exception):
                                self.interrupt_manager.set_always_allow(entry["name"], entry["args"])
                    else:
                        entry["should_execute"] = bool(approval_result)
            except Exception:
                entry["should_execute"] = False

    def _is_parallel_safe(self, tool_name: str, args: dict) -> bool:
        parallel_safe_tools = {"read_file", "grep_search", "git_tools", "task_memory", "web_search"}
        if tool_name not in parallel_safe_tools:
            return False
        if tool_name == "task_memory":
            action = str(args.get("action", "")).strip().lower()
            return action in ("recall", "similar")
        return True

    def _partition_parallel(self, entries: List[Dict[str, Any]]):
        parallel_entries = [e for e in entries if e["should_execute"] and self._is_parallel_safe(e["name"], e["args"]) ]
        sequential_entries = [e for e in entries if e["should_execute"] and not self._is_parallel_safe(e["name"], e["args"]) ]
        return parallel_entries, sequential_entries

    def _emit_skipped(self, tool_calls, entries: List[Dict[str, Any]], pending_for_tools: str) -> None:
        skipped_indices = {e["index"] for e in entries if not e["should_execute"]}
        for idx in skipped_indices:
            tool_call = tool_calls[idx]
            self._add_tool_response(tool_call, f"Tool execution skipped: {pending_for_tools}", is_last_tool=(idx == len(tool_calls) - 1))

    async def _run_parallel(self, parallel_entries: List[Dict[str, Any]], sequential_entries: List[Dict[str, Any]], last_index_overall: int, pending_for_tools: str) -> None:
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

        if not parallel_entries:
            return
        with contextlib.suppress(Exception):
            if hasattr(self.ui_interface, '_spinner_active') and self.ui_interface._spinner_active:
                self.ui_interface.update_spinner_text(f"Running {len(parallel_entries)} tools in parallel…")
        results = await asyncio.gather(*(_run_one(e) for e in parallel_entries))
        for idx, tool_call, content in sorted(results, key=lambda t: t[0]):
            self._add_tool_response(tool_call, content, is_last_tool=(idx == last_index_overall and not sequential_entries))

    async def _run_sequential(self, sequential_entries: List[Dict[str, Any]], last_index_overall: int, pending_for_tools: str) -> None:
        for e in sequential_entries:
            await self._execute_tool(
                e["tool_call"],
                e["args"],
                is_last_tool=(e["index"] == last_index_overall),
                user_response=pending_for_tools,
            )

    def _format_approval_preview(self, tool_name: str, args: Dict[str, Any]) -> str:
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
        # avoid auto-nudges on generic capability/overview replies
        if any(p in text for p in ("i can help you with", "common use cases", "capabilities", "i'm designed to", "i can work with")):
            return None
        if "check the todo.md" in text or "check todo.md" in text:
            return "use read_file to open 'todo.md' now, do not describe."
        # only nudge for directory listing when the assistant commits to act
        if (("ls" in text or "list the " in text or "show the " in text) and
            ("directory" in text or "files" in text or "structure" in text) and
            any(m in text for m in ("i will", "i'll", "let me", "run ", "execute ", "here is the"))):
            return "use cmd_runner with 'ls -la' now, do not describe."
        if "open" in text and ("file" in text or "." in text):
            return "use read_file to open the stated file now, do not describe."
        return None

    async def _execute_tool(self, tool_call, args: Dict, is_last_tool: bool = False, user_response: str = "") -> None:
        tool_args = {k: v for k, v in args.items() if k != 'need_user_approve'}
        
        if hasattr(self.ui_interface, '_spinner_active') and self.ui_interface._spinner_active:
            self.ui_interface.update_spinner_text(f"Running {tool_call.function.name}...")
        else:
            self.ui_interface.display_info(f"🔧 {tool_call.function.name}...")
        
        if user_response:
            tool_args['user_instructions'] = user_response
        
        try:
            tool_response = await self.tool_registry.run_tool(tool_call.function.name, **tool_args)
            
            if hasattr(self.ui_interface, '_spinner_active') and self.ui_interface._spinner_active:
                self.ui_interface.update_spinner_text(f"✓ {tool_call.function.name} completed")
                await asyncio.sleep(0.3)
            else:
                self.ui_interface.display_success(f"{tool_call.function.name} completed successfully")
            response_content = json.dumps(tool_response)
            if user_response:
                response_content += f" (User instructions: {user_response})"
            self._add_tool_response(tool_call, response_content, is_last_tool)
        except Exception as e:
            if hasattr(self.ui_interface, '_spinner_active') and self.ui_interface._spinner_active:
                self.ui_interface.update_spinner_text(f"✗ {tool_call.function.name} failed")
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

    

    def _get_prefs_path(self) -> Path:
        base = Path(os.getcwd()) / ".hakken"
        with contextlib.suppress(Exception):
            base.mkdir(exist_ok=True)
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
            with contextlib.suppress(Exception):
                self.ui_interface.display_success("session saved to task memory")
        except Exception as e:
            with contextlib.suppress(Exception):
                self.ui_interface.display_error(f"autosave failed: {e}")

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
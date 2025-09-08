import json
import sys
import asyncio
import os
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import contextlib
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

from client.openai_client import APIClient, APIConfiguration
from history.conversation_history import ConversationHistoryManager, HistoryConfiguration
from interface.user_interface import HakkenCodeUI
from tools.tool_manager import ToolManager
from tools.human_interrupt import InterruptConfigManager
from prompt.prompt_manager import PromptManager


class ConversationState(Enum):
    WAITING_FOR_INPUT = "waiting"
    PROCESSING = "processing"
    EXECUTING_TOOLS = "executing"
    STREAMING_RESPONSE = "streaming"


@dataclass
class AgentConfig:
    MAX_TEXT_LENGTH: int = 4000
    COMMAND_PREVIEW_MAX_LENGTH: int = 180
    ARGS_PREVIEW_MAX_LENGTH: int = 140
    TOKEN_ESTIMATION_RATIO: int = 4
    INTERRUPT_TIMEOUT: float = 2.0
    STATUS_DISPLAY_DELAY: float = 0.3
    MAX_CONTEXT_BUFFER: int = 1024
    DEFAULT_TEMPERATURE: float = 0.2
    DEFAULT_MAX_TOKENS: int = 8000
    DEFAULT_CONTEXT_LIMIT: int = 120000


@dataclass
class AgentState:
    is_in_task: bool = False
    pending_user_instruction: str = ""
    tools_schema_cache: Optional[Tuple[str, int]] = None
    current_state: ConversationState = ConversationState.WAITING_FOR_INPUT


@dataclass
class ResponseData:
    message: Any
    content: str
    token_usage: Any
    interrupted: bool
    early_exit: bool = False


@dataclass
class ToolExecutionEntry:
    index: int
    tool_call: Any
    name: str
    args: Dict[str, Any]
    should_execute: bool = True


class APIError(Exception):
    pass


class StreamingError(APIError):
    pass


class ToolExecutionError(Exception):
    pass


class AgentConfiguration:
    def __init__(self):
        self.api_config = APIConfiguration.from_environment()
        self.history_config = HistoryConfiguration.from_environment()


class ConversationAgent:
    def __init__(self, config: Optional[AgentConfiguration] = None):
        self.config = config or AgentConfiguration()
        self.agent_config = AgentConfig()
        self.state = AgentState()
        
        self.api_client = APIClient(self.config.api_config)
        self.ui_interface = HakkenCodeUI()
        self.history_manager = ConversationHistoryManager(
            self.config.history_config, 
            self.ui_interface
        )
        self.tool_registry = ToolManager(self.ui_interface, self.history_manager, self)
        self.prompt_manager = PromptManager(self.tool_registry)
        self.interrupt_manager = InterruptConfigManager()
        
        self.logger = logging.getLogger(__name__)

    @property
    def messages(self) -> List[Dict[str, Any]]:
        return self.history_manager.get_current_messages()

    def add_message(self, message: Dict[str, Any]) -> None:
        self.history_manager.add_message(message)

    async def start_conversation(self) -> None:
        try:
            await self._initialize_conversation()
            await self._main_conversation_loop()
        except (KeyboardInterrupt, asyncio.CancelledError):
            self.logger.info("Conversation interrupted by user")
        finally:
            await self._cleanup_conversation()

    async def start_task(self, task_system_prompt: str, user_input: str) -> str:
        self.state.is_in_task = True
        self.history_manager.start_new_chat()
        
        await self._add_system_message(task_system_prompt)
        await self._add_user_message(user_input)

        try:
            await self._process_message_cycle()
            return self.history_manager.finish_chat_get_response()
        finally:
            self.state.is_in_task = False

    async def _initialize_conversation(self) -> None:
        self.ui_interface.display_welcome_header()
        system_prompt = self.prompt_manager.get_system_prompt()
        await self._add_system_message(system_prompt)

    async def _main_conversation_loop(self) -> None:
        # --------------------------------------------------
        # agentic loop: entry point (user input -> process cycle)
        # --------------------------------------------------
        while True:
            user_input = await self.ui_interface.get_user_input(
                "What would you like me to help you with?"
            )
            await self._add_user_message(user_input)
            await self._process_message_cycle()

    async def _cleanup_conversation(self) -> None:
        with contextlib.suppress(Exception):
            await self._maybe_prompt_and_save_on_exit()
        
        with contextlib.suppress(Exception):
            self.ui_interface.restore_session_terminal_mode()
        
        with contextlib.suppress(Exception):
            ctx = self.history_manager.current_context_window
            cost = self.api_client.total_cost
            self.ui_interface.display_exit_panel(ctx, str(cost))

    async def _add_system_message(self, content: str) -> None:
        message = {
            "role": "system", 
            "content": [{"type": "text", "text": content}]
        }
        self.add_message(message)

    async def _add_user_message(self, content: str) -> None:
        message = {
            "role": "user", 
            "content": [{"type": "text", "text": content}]
        }
        self.add_message(message)

    async def _process_message_cycle(self, show_thinking: bool = True) -> None:
        # --------------------------------------------------
        # agentic loop: core cycle (prepare -> stream -> handle -> repeat)
        # --------------------------------------------------
        await self._prepare_request_cycle(show_thinking)
        response_data = await self._get_assistant_response()
        
        if response_data.early_exit:
            return
            
        await self._handle_response_data(response_data)

    async def _prepare_request_cycle(self, show_thinking: bool) -> None:
        self.history_manager.auto_messages_compression()
        
        if show_thinking:
            self._stop_spinner_safely()
            self.ui_interface.start_spinner("Thinking...")
            self._start_interrupt_flow()

    async def _get_assistant_response(self) -> ResponseData:
        request = self._build_openai_request()
        
        try:
            return await self._stream_response(request)
        except StreamingError as e:
            self.logger.error(f"Streaming failed: {e}")
            return await self._fallback_response(request, e)
        except Exception as e:
            self.logger.error(f"Response processing error: {e}")
            return await self._handle_response_error(request, e)

    async def _stream_response(self, request: Dict[str, Any]) -> ResponseData:
        stream_generator = self.api_client.get_completion_stream(request)
        if stream_generator is None:
            raise StreamingError("Stream generator is None - API client returned no response")

        response_data = await self._consume_stream(stream_generator)
        return self._finalize_stream_response(response_data, request)

    async def _fallback_response(self, request: Dict[str, Any], original_error: Exception) -> ResponseData:
        self._stop_spinner_safely()
        self.ui_interface.display_info("🔄 Retrying with non-streaming mode...")
        
        try:
            response_message, token_usage = self.api_client.get_completion(request)
            self.ui_interface.display_assistant_message(response_message.content)
            
            if token_usage:
                self.history_manager.update_token_usage(token_usage)
                
            return ResponseData(
                message=response_message,
                content=response_message.content,
                token_usage=token_usage,
                interrupted=False
            )
        except Exception as fallback_error:
            self.logger.error(f"Non-streaming fallback failed: {fallback_error}")
            error_message = f"Sorry, I encountered a technical problem: {original_error}"
            self.ui_interface.display_error(f"Non-streaming mode also failed: {fallback_error}")
            
            return ResponseData(
                message=self._create_simple_message(error_message),
                content=error_message,
                token_usage=None,
                interrupted=False,
                early_exit=True
            )

    async def _handle_response_error(self, request: Dict[str, Any], error: Exception) -> ResponseData:
        self._stop_spinner_safely()
        self.ui_interface.display_error(f"Response processing error: {error}")
        
        error_message = f"Sorry, I encountered a technical problem: {error}"
        return ResponseData(
            message=self._create_simple_message(error_message),
            content=error_message,
            token_usage=None,
            interrupted=False,
            early_exit=True
        )

    async def _consume_stream(self, stream_generator) -> ResponseData:
        # --------------------------------------------------
        # --- agentic loop: streaming phase (content + interrupts) ---
        # --------------------------------------------------
        response_message = None
        content_builder = []
        token_usage = None
        interrupted = False
        
        self.ui_interface.start_assistant_response()
        spinner_stopped = False

        try:
            async for chunk in self._process_stream_chunks(stream_generator):
                if chunk.get('interrupted'):
                    interrupted = True
                    spinner_stopped = self._ensure_spinner_stopped(spinner_stopped)
                    await self._handle_stream_interruption()
                    break

                if not spinner_stopped:
                    spinner_stopped = self._ensure_spinner_stopped(spinner_stopped)

                chunk_data = chunk.get('data')
                if isinstance(chunk_data, str):
                    content_builder.append(chunk_data)
                    self.ui_interface.stream_content(chunk_data)
                elif hasattr(chunk_data, 'role') and chunk_data.role == 'assistant':
                    response_message = chunk_data
                    if hasattr(chunk_data, 'usage') and chunk_data.usage:
                        token_usage = chunk_data.usage
                elif hasattr(chunk_data, 'usage') and chunk_data.usage:
                    token_usage = chunk_data.usage

        except Exception as stream_error:
            self.ui_interface.display_error(f"Streaming error: {stream_error}")
            if content_builder:
                response_message = self._create_simple_message(''.join(content_builder))
        finally:
            if not spinner_stopped:
                self._stop_spinner_safely()
            self.ui_interface.finish_assistant_response()

        return ResponseData(
            message=response_message,
            content=''.join(content_builder),
            token_usage=token_usage,
            interrupted=interrupted
        )

    async def _process_stream_chunks(self, stream_generator):
        for chunk in stream_generator:
            interrupt_text = self._safe_poll_interrupt()
            if interrupt_text is not None and interrupt_text.strip() == "ESC":
                yield {'interrupted': True}
                return
            
            yield {'data': chunk}

    async def _handle_stream_interruption(self) -> None:
        instruction = await self._capture_instruction_interactively()
        if instruction:
            with contextlib.suppress(Exception):
                self.ui_interface.start_spinner("Applying instruction...")
            self.state.pending_user_instruction = instruction

    def _finalize_stream_response(self, response_data: ResponseData, request: Dict[str, Any]) -> ResponseData:
        if response_data.message is not None and self._has_tool_calls(response_data.message):
            return response_data

        if response_data.message is None:
            response_data.message = self._create_fallback_message(response_data)
            return response_data

        if not response_data.content.strip():
            return self._handle_empty_content(response_data, request)

        return response_data

    def _create_fallback_message(self, response_data: ResponseData) -> Any:
        if response_data.content.strip():
            return self._create_simple_message(response_data.content)
        elif not response_data.interrupted:
            return self._create_simple_message("Sorry, I didn't receive a complete response.")
        else:
            return self._create_simple_message("")

    def _handle_empty_content(self, response_data: ResponseData, request: Dict[str, Any]) -> ResponseData:
        final_content = getattr(response_data.message, 'content', '')
        
        if isinstance(final_content, str) and final_content.strip():
            self.ui_interface.display_assistant_message(final_content)
            return response_data

        if not response_data.interrupted:
            return self._attempt_non_streaming_fallback(response_data, request)
        else:
            response_data.message = self._create_simple_message("")
            return response_data

    def _attempt_non_streaming_fallback(self, response_data: ResponseData, request: Dict[str, Any]) -> ResponseData:
        try:
            self.ui_interface.display_info("No streamed content; retrying without streaming…")
            fallback_msg, fallback_usage = self.api_client.get_completion(request)
            self.ui_interface.display_assistant_message(fallback_msg.content)
            
            if fallback_usage:
                response_data.token_usage = fallback_usage
                self.history_manager.update_token_usage(fallback_usage)
                
            response_data.message = fallback_msg
            return response_data
        except Exception as fb_err:
            self.ui_interface.display_error(f"Non-streaming fallback failed: {fb_err}")
            error_msg = f"Sorry, I encountered a technical problem: {fb_err}"
            response_data.message = self._create_simple_message(error_msg)
            response_data.early_exit = True
            self.ui_interface.display_assistant_message(error_msg)
            return response_data

    async def _handle_response_data(self, response_data: ResponseData) -> None:
        self._stop_interrupt_listener_safely()
        
        if response_data.token_usage:
            self.history_manager.update_token_usage(response_data.token_usage)

        self._save_assistant_message(response_data)
        self.history_manager.auto_messages_compression()

        await self._execute_post_response_flow(response_data)

    def _save_assistant_message(self, response_data: ResponseData) -> None:
        if response_data.interrupted and not response_data.content.strip():
            return

        content_to_save = self._determine_content_to_save(response_data)
        assistant_message = {
            "role": "assistant",
            "content": content_to_save,
            "tool_calls": self._extract_tool_calls_safe(response_data.message)
        }
        self.add_message(assistant_message)

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

    async def _execute_post_response_flow(self, response_data: ResponseData) -> None:

        # --------------------------------------------------
        # agentic loop: branching & re-entry
        # --------------------------------------------------
        # --------------------------------------------------
        # interrupted -> re-enter cycle; tools -> execute, then re-enter; otherwise nudge/pending -> possibly re-enter
        # --------------------------------------------------

        if response_data.interrupted:
            await self._process_message_cycle(show_thinking=True)
            return

        if self._has_tool_calls(response_data.message):
            await self._handle_tool_execution(response_data.message)
            await self._process_message_cycle(show_thinking=True)
            return

        await self._check_for_action_nudges()
        await self._handle_pending_instructions()

    async def _handle_tool_execution(self, response_message: Any) -> None:
        # --------------------------------------------------
        # agentic loop: tool execution phase (parallel + sequential)
        # --------------------------------------------------
        if not hasattr(self.ui_interface, '_spinner_active') or not self.ui_interface._spinner_active:
            self.ui_interface.start_spinner("Processing…")
            self._start_interrupt_flow()
        
        tool_calls = self._extract_tool_calls(response_message)
        await self._process_tool_calls(tool_calls)

    async def _check_for_action_nudges(self) -> None:
        try:
            last_msg = self.messages[-1]
            last_content = last_msg.get("content", "") if isinstance(last_msg, dict) else ""
            nudge_text = self._derive_action_nudge(str(last_content))
            
            if nudge_text:
                await self._add_user_message(nudge_text)
                await self._process_message_cycle(show_thinking=True)
        except Exception as e:
            self.logger.error(f"Error checking action nudges: {e}")

    async def _handle_pending_instructions(self) -> None:
        pending_instruction = self.state.pending_user_instruction.strip()
        if pending_instruction:
            self.state.pending_user_instruction = ""
            await self._add_user_message(pending_instruction)
            await self._process_message_cycle(show_thinking=True)

    def _build_openai_request(self) -> Dict[str, Any]:
        messages = self._get_messages_with_cache_mark()
        tools_description = self.tool_registry.get_tools_description()
        
        estimated_input_tokens = self._estimate_total_tokens(messages, tools_description)
        limits = self._get_openai_env_limits()
        max_output_tokens = self._compute_max_output_tokens(estimated_input_tokens, limits)
        
        return {
            "messages": messages,
            "tools": tools_description,
            "max_tokens": max_output_tokens,
            "temperature": self._get_temperature(),
            "tool_choice": "auto",
        }

    def _estimate_total_tokens(self, messages: List[Dict[str, Any]], tools_description: List[Dict[str, Any]]) -> int:
        message_tokens = self._estimate_tokens(messages)
        tools_tokens = self._estimate_tools_tokens(tools_description)
        return message_tokens + tools_tokens

    def _get_messages_with_cache_mark(self) -> List[Dict[str, Any]]:
        messages = self.history_manager.get_current_messages()
        if messages and "content" in messages[-1] and messages[-1]["content"]:
            content = messages[-1]["content"]
            if isinstance(content, list) and isinstance(content[-1], dict):
                content[-1]["cache_control"] = {"type": "ephemeral"}
        return messages

    async def _process_tool_calls(self, tool_calls: List[Any]) -> None:
        # --------------------------------------------------
        # agentic loop: tool execution phase (parallel + sequential)
        # --------------------------------------------------
        pending_instruction = self._extract_pending_instruction()
        entries = self._parse_tool_calls(tool_calls)
        await self._apply_approvals(entries)

        parallel_entries, sequential_entries = self._partition_tool_entries(entries)
        self._handle_skipped_tools(tool_calls, entries, pending_instruction)

        last_index = len(tool_calls) - 1 if tool_calls else -1
        await self._execute_parallel_tools(parallel_entries, sequential_entries, last_index, pending_instruction)
        await self._execute_sequential_tools(sequential_entries, last_index, pending_instruction)

    def _extract_pending_instruction(self) -> str:
        pending = self.state.pending_user_instruction.strip()
        if pending:
            self.state.pending_user_instruction = ""
        return pending

    def _parse_tool_calls(self, tool_calls: List[Any]) -> List[ToolExecutionEntry]:
        entries = []
        for idx, tool_call in enumerate(tool_calls):
            try:
                args = json.loads(tool_call.function.arguments)
                entries.append(ToolExecutionEntry(
                    index=idx,
                    tool_call=tool_call,
                    name=tool_call.function.name,
                    args=args,
                    should_execute=True
                ))
            except json.JSONDecodeError as e:
                self.ui_interface.display_error(f"Tool parameter parsing failed: {e}")
                self._add_tool_response(
                    tool_call, 
                    "Tool call failed due to JSONDecodeError", 
                    is_last_tool=(idx == len(tool_calls) - 1)
                )
        return entries

    async def _apply_approvals(self, entries: List[ToolExecutionEntry]) -> None:
        for entry in entries:
            try:
                if self.interrupt_manager.requires_approval(entry.name, entry.args):
                    entry.should_execute = await self._get_tool_approval(entry)
            except Exception as e:
                self.logger.error(f"Approval process failed for {entry.name}: {e}")
                entry.should_execute = False

    async def _get_tool_approval(self, entry: ToolExecutionEntry) -> bool:
        approval_content = self._format_approval_preview(entry.name, entry.args)
        approval_result = await self.ui_interface.confirm_action(approval_content)
        
        if isinstance(approval_result, str):
            decision = approval_result.strip().lower()
            if decision == "always":
                with contextlib.suppress(Exception):
                    self.interrupt_manager.set_always_allow(entry.name, entry.args)
            return decision in ("yes", "always")
        
        return bool(approval_result)

    def _partition_tool_entries(self, entries: List[ToolExecutionEntry]) -> Tuple[List[ToolExecutionEntry], List[ToolExecutionEntry]]:
        parallel_entries = [
            e for e in entries 
            if e.should_execute and self._is_parallel_safe(e.name, e.args)
        ]
        sequential_entries = [
            e for e in entries 
            if e.should_execute and not self._is_parallel_safe(e.name, e.args)
        ]
        return parallel_entries, sequential_entries

    def _handle_skipped_tools(self, tool_calls: List[Any], entries: List[ToolExecutionEntry], pending_instruction: str) -> None:
        skipped_indices = {e.index for e in entries if not e.should_execute}
        for idx in skipped_indices:
            tool_call = tool_calls[idx]
            self._add_tool_response(
                tool_call, 
                f"Tool execution skipped: {pending_instruction}", 
                is_last_tool=(idx == len(tool_calls) - 1)
            )

    async def _execute_parallel_tools(
        self, 
        parallel_entries: List[ToolExecutionEntry], 
        sequential_entries: List[ToolExecutionEntry], 
        last_index: int, 
        pending_instruction: str
    ) -> None:
        if not parallel_entries:
            return

        if hasattr(self.ui_interface, '_spinner_active') and self.ui_interface._spinner_active:
            self.ui_interface.update_spinner_text(f"Running {len(parallel_entries)} tools in parallel…")

        tasks = [self._execute_single_tool_async(entry, pending_instruction) for entry in parallel_entries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            entry = parallel_entries[i]
            if isinstance(result, Exception):
                content = f"Tool call failed, fail reason: {str(result)}"
                self.logger.error(f"Parallel tool {entry.name} failed: {result}")
            else:
                content = json.dumps(result)
            
            self._add_tool_response(
                entry.tool_call, 
                content, 
                is_last_tool=(entry.index == last_index and not sequential_entries)
            )

    async def _execute_sequential_tools(
        self, 
        sequential_entries: List[ToolExecutionEntry], 
        last_index: int, 
        pending_instruction: str
    ) -> None:
        for entry in sequential_entries:
            await self._execute_single_tool(
                entry.tool_call,
                entry.args,
                is_last_tool=(entry.index == last_index),
                user_response=pending_instruction,
            )

    async def _execute_single_tool_async(self, entry: ToolExecutionEntry, user_response: str) -> Any:
        tool_args = self._prepare_tool_args(entry.args, user_response)
        return await self.tool_registry.run_tool(entry.name, **tool_args)

    async def _execute_single_tool(
        self, 
        tool_call: Any, 
        args: Dict[str, Any], 
        is_last_tool: bool = False, 
        user_response: str = ""
    ) -> None:
        tool_args = self._prepare_tool_args(args, user_response)
        
        self._update_tool_status(tool_call.function.name, "running")
        
        try:
            tool_response = await self.tool_registry.run_tool(tool_call.function.name, **tool_args)
            self._update_tool_status(tool_call.function.name, "completed")
            await asyncio.sleep(self.agent_config.STATUS_DISPLAY_DELAY)
            
            response_content = json.dumps(tool_response)
            if user_response:
                response_content += f" (User instructions: {user_response})"
                
            self._add_tool_response(tool_call, response_content, is_last_tool)
            
        except Exception as e:
            self.logger.error(f"Tool {tool_call.function.name} failed: {e}")
            self._update_tool_status(tool_call.function.name, "failed")
            await asyncio.sleep(self.agent_config.STATUS_DISPLAY_DELAY)
            
            self._add_tool_response(
                tool_call, 
                f"Tool call failed, fail reason: {str(e)}", 
                is_last_tool
            )

    def _prepare_tool_args(self, args: Dict[str, Any], user_response: str) -> Dict[str, Any]:
        tool_args = {k: v for k, v in args.items() if k != 'need_user_approve'}
        if user_response:
            tool_args['user_instructions'] = user_response
        return tool_args

    def _update_tool_status(self, tool_name: str, status: str) -> None:
        status_messages = {
            "running": f"Running {tool_name}...",
            "completed": f"✓ {tool_name} completed",
            "failed": f"✗ {tool_name} failed"
        }
        
        if hasattr(self.ui_interface, '_spinner_active') and self.ui_interface._spinner_active:
            self.ui_interface.update_spinner_text(status_messages[status])
        else:
            if status == "completed":
                self.ui_interface.display_success(f"{tool_name} completed successfully")
            elif status == "failed":
                self.ui_interface.display_error(f"{tool_name} failed")
            else:
                self.ui_interface.display_info(f"🔧 {tool_name}...")

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
            self._stop_spinner_safely()
            return True
        return spinner_stopped

    def _stop_spinner_safely(self) -> None:
        with contextlib.suppress(Exception):
            self.ui_interface.stop_spinner()

    async def _capture_instruction_interactively(self) -> Optional[str]:
        try:
            self.ui_interface.pause_stream_display()
            self.ui_interface.flush_interrupts()
            
            instruction = self.ui_interface.wait_for_interrupt(
                timeout=self.agent_config.INTERRUPT_TIMEOUT
            )
            
            if not instruction:
                self._stop_interrupt_listener_safely()
                instruction = self.ui_interface.capture_instruction()
                with contextlib.suppress(Exception):
                    self.ui_interface.start_interrupt_listener()
                    
            return instruction
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
        return max(0, (len(serialized) + self.agent_config.TOKEN_ESTIMATION_RATIO - 1) // self.agent_config.TOKEN_ESTIMATION_RATIO)

    def _estimate_tools_tokens(self, tools_description: List[Dict[str, Any]]) -> int:
        try:
            serialized = json.dumps(tools_description, sort_keys=True, ensure_ascii=False)
            tools_hash = hashlib.md5(serialized.encode()).hexdigest()
            
            if self.state.tools_schema_cache is not None:
                cached_hash, cached_tokens = self.state.tools_schema_cache
                if cached_hash == tools_hash:
                    return cached_tokens
            
            estimated_tokens = self._estimate_tokens(tools_description)
            self.state.tools_schema_cache = (tools_hash, estimated_tokens)
            return estimated_tokens
        except Exception:
            return self._estimate_tokens(tools_description)

    def _get_openai_env_limits(self) -> Dict[str, int]:
        return {
            "user_requested_max_out": int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", str(self.agent_config.DEFAULT_MAX_TOKENS))),
            "context_limit": int(os.getenv("OPENAI_CONTEXT_LIMIT", str(self.agent_config.DEFAULT_CONTEXT_LIMIT))),
            "buffer_tokens": int(os.getenv("OPENAI_OUTPUT_BUFFER_TOKENS", str(self.agent_config.MAX_CONTEXT_BUFFER))),
        }

    def _compute_max_output_tokens(self, estimated_input_tokens: int, limits: Dict[str, int]) -> int:
        safe_output_cap = max(
            256, 
            limits["context_limit"] - estimated_input_tokens - limits["buffer_tokens"]
        )
        return max(256, min(limits["user_requested_max_out"], safe_output_cap))

    def _get_temperature(self) -> float:
        return float(os.getenv("OPENAI_TEMPERATURE", str(self.agent_config.DEFAULT_TEMPERATURE)))

    def _has_tool_calls(self, response_message: Any) -> bool:
        return bool(hasattr(response_message, 'tool_calls') and response_message.tool_calls)

    def _extract_tool_calls(self, response_message: Any) -> List[Any]:
        return response_message.tool_calls if hasattr(response_message, 'tool_calls') and response_message.tool_calls else []

    def _is_parallel_safe(self, tool_name: str, args: Dict[str, Any]) -> bool:
        parallel_safe_tools = {"read_file", "grep_search", "git_tools", "task_memory", "web_search"}
        if tool_name not in parallel_safe_tools:
            return False
        if tool_name == "task_memory":
            action = str(args.get("action", "")).strip().lower()
            return action in ("recall", "similar")
        return True

    def _format_approval_preview(self, tool_name: str, args: Dict[str, Any]) -> str:
        try:
            preview_args = self._create_preview_args(tool_name, args)
            return f"Tool: {tool_name}, args: {preview_args}"
        except Exception:
            return f"Tool: {tool_name}, args: {args}"

    def _create_preview_args(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        preview_args: Dict[str, Any] = {}
        
        if tool_name == "cmd_runner":
            return self._format_command_preview(args)
        
        for k, v in args.items():
            if isinstance(v, str):
                preview_args[k] = self._truncate_string(v, self.agent_config.ARGS_PREVIEW_MAX_LENGTH)
            else:
                preview_args[k] = v
        
        return preview_args

    def _format_command_preview(self, args: Dict[str, Any]) -> Dict[str, Any]:
        cmd = args.get("command", "")
        if isinstance(cmd, str):
            normalized = cmd.replace("\n", " ")
            truncated = self._truncate_string(normalized, self.agent_config.COMMAND_PREVIEW_MAX_LENGTH)
            return {
                "command": truncated,
                "length": len(cmd)
            }
        else:
            return {"command": str(cmd)}

    def _truncate_string(self, text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        return text[:max_length].rstrip() + "…"

    def _derive_action_nudge(self, assistant_text: str) -> Optional[str]:
        text = assistant_text.lower()
        
        if not text or len(text) > self.agent_config.MAX_TEXT_LENGTH:
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

    def _add_tool_response(self, tool_call: Any, content: str, is_last_tool: bool = False) -> None:
        # --- agentic loop: tool result → message (+ reminder) back to llm ---
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

    def _create_simple_message(self, content: str) -> Any:
        class SimpleMessage:
            def __init__(self, content: str):
                self.content = content
                self.role = "assistant"
                self.tool_calls = None
        
        return SimpleMessage(content)

    def _get_prefs_path(self) -> Path:
        base = Path(os.getcwd()) / ".hakken"
        with contextlib.suppress(Exception):
            base.mkdir(exist_ok=True)
        return base / "agent_prefs.json"

    def _load_prefs(self) -> Dict[str, Any]:
        path = self._get_prefs_path()
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8") or "{}")
        except Exception as e:
            self.logger.error(f"Failed to load preferences: {e}")
        return {}

    def _save_prefs(self, data: Dict[str, Any]) -> None:
        path = self._get_prefs_path()
        try:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), 
                encoding="utf-8"
            )
        except Exception as e:
            self.logger.error(f"Failed to save preferences: {e}")

    async def _save_task_memory_on_exit(self) -> None:
        try:
            context_data = self._collect_exit_context()
            await self.tool_registry.run_tool(
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
                return self._truncate_string(text.strip(), 400)
        
        return ""

    def _get_environment_summary(self) -> str:
        try:
            env = self.prompt_manager.environment_collector.collect_all()
            return f"cwd: {env.working_directory}\nplatform: {env.platform}"
        except Exception as e:
            self.logger.error(f"Failed to collect environment: {e}")
            return ""

    async def _maybe_prompt_and_save_on_exit(self) -> None:
        prefs = self._load_prefs()
        
        if prefs.get("exit_auto_save", False):
            await self._save_task_memory_on_exit()
            return

        try:
            result = await self.ui_interface.confirm_action(
                "Save this session to task memory before exit?"
            )
            await self._handle_save_decision(result, prefs)
        except Exception as e:
            self.logger.error(f"Save prompt failed: {e}")

    async def _handle_save_decision(self, result: Union[str, bool], prefs: Dict[str, Any]) -> None:
        if isinstance(result, str):
            decision = result.strip().lower()
            if decision == "always":
                prefs["exit_auto_save"] = True
                self._save_prefs(prefs)
                await self._save_task_memory_on_exit()
            elif decision == "yes":
                await self._save_task_memory_on_exit()
        elif bool(result):
            await self._save_task_memory_on_exit()
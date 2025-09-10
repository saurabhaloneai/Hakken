import json
import asyncio
import contextlib
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

from client.openai_client import APIClient
from interface.user_interface import HakkenCodeUI
from history.conversation_history import ConversationHistoryManager
from agent.state_manager import StateManager


@dataclass
class ResponseData:
    message: Any
    content: str
    token_usage: Any
    interrupted: bool
    early_exit: bool = False


class APIError(Exception):
    pass


class StreamingError(APIError):
    pass


class ResponseHandler:
    
    def __init__(self, api_client: APIClient, ui_interface: HakkenCodeUI, 
                 history_manager: ConversationHistoryManager, state_manager: StateManager):
        self.api_client = api_client
        self.ui_interface = ui_interface
        self.history_manager = history_manager
        self.state_manager = state_manager
        self.logger = logging.getLogger(__name__)
    
    def build_openai_request(self, tool_registry) -> Dict[str, Any]:
        messages = self._get_messages_with_cache_mark()
        tools_description = tool_registry.get_tools_description()
        
        estimated_input_tokens = self.state_manager.estimate_total_tokens(messages, tools_description)
        limits = self.state_manager.get_openai_env_limits()
        max_output_tokens = self.state_manager.compute_max_output_tokens(estimated_input_tokens, limits)
        
        return {
            "messages": messages,
            "tools": tools_description,
            "max_tokens": max_output_tokens,
            "temperature": self.state_manager.get_temperature(),
            "tool_choice": "auto",
        }
    
    def _get_messages_with_cache_mark(self) -> List[Dict[str, Any]]:
        messages = self.history_manager.get_current_messages()
        if messages and "content" in messages[-1] and messages[-1]["content"]:
            content = messages[-1]["content"]
            if isinstance(content, list) and isinstance(content[-1], dict):
                content[-1]["cache_control"] = {"type": "ephemeral"}
        return messages
    
    async def get_assistant_response(self, request: Dict[str, Any]) -> ResponseData:
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
    
    async def _consume_stream(self, stream_generator) -> ResponseData:
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
            if isinstance(chunk, str) and not chunk:
                try:
                    import asyncio as _asyncio
                    await _asyncio.sleep(0)
                except Exception:
                    pass
                continue
            interrupt_text = self._safe_poll_interrupt()
            if interrupt_text is not None and interrupt_text.strip() == "ESC":
                yield {'interrupted': True}
                return
            
            yield {'data': chunk}
    
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
            response_data.content = fallback_msg.content  # Update content as well
            response_data.interrupted = False  # Ensure it's not marked as interrupted
            return response_data
        except Exception as fb_err:
            self.ui_interface.display_error(f"Non-streaming fallback failed: {fb_err}")
            error_msg = f"Sorry, I encountered a technical problem: {fb_err}"
            response_data.message = self._create_simple_message(error_msg)
            response_data.early_exit = True
            self.ui_interface.display_assistant_message(error_msg)
            return response_data
    
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
    
    def _has_tool_calls(self, response_message: Any) -> bool:
        return bool(hasattr(response_message, 'tool_calls') and response_message.tool_calls)
    
    def _create_simple_message(self, content: str) -> Any:
        class SimpleMessage:
            def __init__(self, content: str):
                self.content = content
                self.role = "assistant"
                self.tool_calls = None
        
        return SimpleMessage(content)
    
    def _ensure_spinner_stopped(self, spinner_stopped: bool) -> bool:
        if not spinner_stopped:
            self._stop_spinner_safely()
            return True
        return spinner_stopped
    
    def _stop_spinner_safely(self) -> None:
        with contextlib.suppress(Exception):
            self.ui_interface.stop_spinner()
    
    def _safe_poll_interrupt(self) -> Optional[str]:
        try:
            return self.ui_interface.poll_interrupt()
        except Exception:
            return None

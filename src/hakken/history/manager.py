from abc import ABC, abstractmethod
import copy
from dataclasses import dataclass
import os
from typing import TYPE_CHECKING, Dict, Optional, List, Any
from dotenv import load_dotenv
from enum import Enum
from hakken.history.tracer import TraceLogger, TraceSession

if TYPE_CHECKING:
    from hakken.terminal_bridge import UIManager
    from hakken.core.client import APIClient

load_dotenv()


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    TOOL = "tool"
    ASSISTANT = "assistant"


class Crop_Direction(str, Enum):
    TOP = "top"
    BOTTOM = "bottom"


class BaseHistoryManager(ABC):
    def __init__(self):
        self.messages_history = [[]]
        self.history_token_usage = []

    @abstractmethod
    def add_message(self, message) -> None:
        pass

    @abstractmethod
    def update_token_usage(self, token_usage) -> None:
        pass

    @abstractmethod
    def get_current_messages(self) -> any:
        pass

    def auto_messages_compression(self) -> None:
        if self._requires_compression():
            self._compress_current_message()

    @abstractmethod
    def _requires_compression(self) -> bool:
        pass

    @abstractmethod
    def _compress_current_message(self) -> None:
        pass

    @abstractmethod
    def start_new_chat(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        pass

    @abstractmethod
    def finish_chat_get_response(self) -> str:
        pass


class HistoryManager(BaseHistoryManager):
    def __init__(
        self, 
        ui_manager: "UIManager",
        api_client: Optional["APIClient"] = None,
        model_max_tokens: int = 200, 
        compress_threshold: float = 0.8,
        trace_logger: Optional[TraceLogger] = None,
        initial_trace_metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__()
        self._ui_manager = ui_manager
        self._api_client = api_client
        self._model_max_tokens = int(os.getenv("MODEL_MAX_TOKENS", model_max_tokens)) * 1024
        self._compress_threshold = float(os.getenv("COMPRESS_THRESHOLD", compress_threshold))
        self._trace_logger = trace_logger or TraceLogger()
        self._trace_sessions: List[Optional[TraceSession]] = []
        self._initialize_trace_session(initial_trace_metadata or {"mode": "interactive", "chat_index": 0})
        self._tool_result_count = 0

    def add_message(self, message) -> None:
        self.messages_history[-1].append(message)
        if self._trace_logger:
            self._trace_logger.log_message(
                self._current_trace_session,
                message,
                {"message_index": len(self.messages_history[-1]) - 1}
            )
        
        if message.get('role') == Role.TOOL:
            self.auto_clear_tool_results()
    
    def set_api_client(self, api_client: "APIClient") -> None:
        self._api_client = api_client

    def crop_message(self, crop_direction: Crop_Direction, crop_amount: int) -> str:
        current_messages = self.messages_history[-1]
        
        if len(current_messages) <= 1:
            return "Cannot crop: insufficient messages"
        
        if len(current_messages) < crop_amount + 2:
            return "Cannot crop: invalid crop amount"

        latest_user_index = -1
        for i in range(len(current_messages) - 1, -1, -1):
            if current_messages[i]['role'] == Role.USER:
                latest_user_index = i
                break
        
        if latest_user_index == -1:
            return "Cannot crop: no user messages found"

        if crop_direction == Crop_Direction.TOP:
            max_crop_amount = latest_user_index
        else:
            max_crop_amount = len(current_messages) - latest_user_index - 1
        
        if crop_amount > max_crop_amount:
            return "Cannot crop: can't crop the latest user message"

        if crop_direction == Crop_Direction.TOP:
            system_messages = [msg for msg in current_messages if msg['role'] == Role.SYSTEM]
            cropped_messages = system_messages + current_messages[crop_amount:]
        else:
            cropped_messages = current_messages[:-crop_amount]
        
        self.messages_history[-1] = cropped_messages
        return "Crop message successful"

    @property
    def current_context_window(self):
        if not self.history_token_usage or self._model_max_tokens == 0:
            return "0.0"
        return f"{100 * self.history_token_usage[-1].total_tokens / self._model_max_tokens:.1f}"

    @property
    def trace_logger(self) -> TraceLogger:
        return self._trace_logger

    def update_token_usage(self, token_usage) -> None:
        token_usage = TokenUsage(
            input_tokens=token_usage.prompt_tokens,
            output_tokens=token_usage.completion_tokens,
            total_tokens=token_usage.total_tokens
        )

        if len(self.history_token_usage) == 0:
            self.history_token_usage.append(token_usage)
        else:
            self.history_token_usage[-1] = token_usage
        if self._trace_logger:
            self._trace_logger.log_event(
                self._current_trace_session,
                "token_usage",
                {
                    "input_tokens": token_usage.input_tokens,
                    "output_tokens": token_usage.output_tokens,
                    "total_tokens": token_usage.total_tokens,
                }
            )

    def get_current_messages(self) -> any:
        return copy.deepcopy(self.messages_history[-1])

    def start_new_chat(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.messages_history.append([])
        self.history_token_usage.append(TokenUsage(0, 0, 0))
        trace_metadata = {"mode": "task", "chat_index": len(self._trace_sessions)}
        if metadata:
            trace_metadata.update(metadata)
        self._append_trace_session(trace_metadata)

    def finish_chat_get_response(self) -> str:
        assert len(self.messages_history) >= 2, "there must more than or equal to 2 messages in history"
        task_messages = self.messages_history.pop()
        self.history_token_usage.pop()
        finished_session = self._trace_sessions.pop() if self._trace_sessions else None
        if finished_session and self._trace_logger:
            self._trace_logger.log_event(
                finished_session,
                "session_end",
                {"message_count": len(task_messages)}
            )
        response = task_messages[-1]["content"]
        return response

    def _requires_compression(self) -> bool:
        if self._compress_threshold and self.history_token_usage:
            current_usage = self.history_token_usage[-1]
            return current_usage.total_tokens > self._compress_threshold * self._model_max_tokens
        return False

    def _compress_current_message(self) -> None:
        self._ui_manager.print_assistant_message("History context too long, compressing...")

        current_messages = self.messages_history[-1]
        user_indices = self._get_user_message_indices(current_messages)
        
        if len(user_indices) > 1:
            self._compress_multiple_sessions_with_summary(current_messages, user_indices)
        elif len(user_indices) == 1:
            self._compress_single_session(current_messages, user_indices[0], 3)

    @property
    def _current_trace_session(self) -> Optional[TraceSession]:
        return self._trace_sessions[-1] if self._trace_sessions else None

    def _initialize_trace_session(self, metadata: Dict[str, Any]) -> None:
        self._append_trace_session(metadata)

    def _append_trace_session(self, metadata: Dict[str, Any]) -> None:
        session = self._trace_logger.start_session(metadata) if self._trace_logger else None
        self._trace_sessions.append(session)
    
    def _get_user_message_indices(self, messages: list) -> list[int]:
        return [i for i, msg in enumerate(messages) if msg.get('role') == Role.USER]
    
    def _compress_multiple_sessions(self, messages: list, user_indices: list[int]) -> None:
        second_oldest_user_index = user_indices[1]

        system_messages = [
            msg for msg in messages[:second_oldest_user_index] 
            if msg.get('role') == Role.SYSTEM
        ]
        recent_messages = messages[second_oldest_user_index:]

        self.messages_history[-1] = (
            system_messages + self._create_compression_notice(messages) + recent_messages
        )

    def _compress_single_session(
        self, messages: list, user_index: int, delete_message_num: int
    ) -> None:
        system_messages = [
            msg for msg in messages[:user_index] 
            if msg.get('role') == Role.SYSTEM
        ]
        
        start_index = min(user_index + 1 + delete_message_num, len(messages))
        user_message = (
            [messages[user_index]] + 
            self._create_compression_notice(messages) + 
            messages[start_index:]
        )

        self.messages_history[-1] = system_messages + user_message

    def _create_compression_notice(self, messages: list) -> list:
        compression_notice = {
            "role": Role.USER,
            "content": "[Previous conversation history has been compressed to save context window space]"
        }
        return [compression_notice]
    
    def clear_old_tool_results(self, keep_last_n: int = 5) -> int:
        current_messages = self.messages_history[-1]
        
        tool_indices = [
            i for i, msg in enumerate(current_messages) 
            if msg.get('role') == Role.TOOL
        ]
        
        if len(tool_indices) <= keep_last_n:
            return 0
        
        indices_to_clear = tool_indices[:-keep_last_n]
        cleared_count = 0
        
        for idx in indices_to_clear:
            if current_messages[idx]['content'] != "[Tool result cleared to save context]":
                current_messages[idx]['content'] = "[Tool result cleared to save context]"
                cleared_count += 1
        
        return cleared_count
    
    def auto_clear_tool_results(self) -> None:
        self._tool_result_count += 1
        if self._tool_result_count >= 10:
            cleared = self.clear_old_tool_results(keep_last_n=5)
            if cleared > 0:
                self._ui_manager.print_assistant_message(
                    f"Cleared {cleared} old tool results to optimize context."
                )
            self._tool_result_count = 0
    
    def _format_messages_for_summary(self, messages: list) -> str:
        formatted_lines = []
        
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            
            if role == Role.SYSTEM:
                continue
            
            if role == Role.TOOL:
                if content != "[Tool result cleared to save context]":
                    tool_name = msg.get('name', 'unknown_tool')
                    formatted_lines.append(f"Tool({tool_name}): {content[:200]}...")
            else:
                formatted_lines.append(f"{role.upper()}: {content}")
        
        return "\n".join(formatted_lines)
    
    def _compress_with_llm_summary(self, messages_to_compress: list) -> str:
        if not self._api_client:
            return "[Previous conversation compressed (LLM summarization unavailable)]"
        
        history_text = self._format_messages_for_summary(messages_to_compress)
        
        summary_prompt = f"""Analyze this conversation and create a concise summary preserving:

1. Key architectural decisions
2. Unresolved bugs or issues  
3. Important implementation details
4. User preferences and requirements
5. Critical context for continuing work

Discard redundant tool outputs and repeated information.

Conversation:
{history_text}

Provide focused summary (200-400 tokens):"""
        
        request_params = {
            "messages": [{"role": "user", "content": summary_prompt}],
            "max_tokens": 500,
            "temperature": 0.3
        }
        
        response, _ = self._api_client.get_completion(request_params)
        return response.content if response.content else "[Summary generation failed]"
    
    def _compress_multiple_sessions_with_summary(self, messages: list, user_indices: list[int]) -> None:
        second_oldest_user_index = user_indices[1]
        
        messages_to_compress = messages[:second_oldest_user_index]
        system_messages = [
            msg for msg in messages_to_compress
            if msg.get('role') == Role.SYSTEM
        ]
        
        summary = self._compress_with_llm_summary(messages_to_compress)
        summary_message = {
            "role": Role.USER,
            "content": f"[Previous Session Summary]\n{summary}"
        }
        
        recent_messages = messages[second_oldest_user_index:]
        self.messages_history[-1] = system_messages + [summary_message] + recent_messages
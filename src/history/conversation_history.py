
import copy
from dataclasses import dataclass
import os
from dotenv import load_dotenv
from enum import Enum
from typing import List, Any, Optional

load_dotenv()


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass 
class HistoryConfiguration:
    model_max_tokens: int
    compress_threshold: float
    
    @classmethod
    def from_environment(cls, model_max_tokens: int = 200, compress_threshold: float = 0.8) -> 'HistoryConfiguration':
        max_tokens = int(os.getenv("MODEL_MAX_TOKENS", model_max_tokens)) * 1024
        threshold = float(os.getenv("COMPRESS_THRESHOLD", compress_threshold))
        return cls(model_max_tokens=max_tokens, compress_threshold=threshold)


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    TOOL = "tool"
    ASSISTANT = "assistant"


class CropDirection(str, Enum):
    TOP = "top"
    BOTTOM = "bottom"


class ConversationHistoryManager:
    
    def __init__(self, config: HistoryConfiguration, ui_interface=None):
        self.messages_history = [[]]
        self.history_token_usage = []
        self.config = config
        self.ui_interface = ui_interface

    def add_message(self, message) -> None:
        self.messages_history[-1].append(message)

    def auto_messages_compression(self) -> None:
        if self._requires_compression():
            self._compress_current_message()

    def crop_message(self, crop_direction: CropDirection, crop_amount: int) -> str:  
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

        if crop_direction == CropDirection.TOP:
            max_crop_amount = latest_user_index
        else:  # BOTTOM
            max_crop_amount = len(current_messages) - latest_user_index - 1
            
        if crop_amount > max_crop_amount:
            return "Cannot crop: can't crop the latest user message"

        if crop_direction == CropDirection.TOP:
            system_messages = [msg for msg in current_messages if msg['role'] == Role.SYSTEM]
            cropped_messages = system_messages + current_messages[crop_amount:]
        else:  # BOTTOM
            cropped_messages = current_messages[:-crop_amount]
        
        self.messages_history[-1] = cropped_messages
        return "Crop message successful"

    @property                                                                                                                       
    def current_context_window(self) -> str:                                                                                               
        if not self.history_token_usage or self.config.model_max_tokens == 0:                                                             
            return "0.0"                                                                                                            
        return f"{100 * self.history_token_usage[-1].total_tokens / self.config.model_max_tokens:.1f}" 

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

    def get_current_messages(self) -> Any:
        return copy.deepcopy(self.messages_history[-1])

    def start_new_chat(self) -> None:
        self.messages_history.append([])
        self.history_token_usage.append(TokenUsage(0, 0, 0))

    def finish_chat_get_response(self) -> str:
        assert len(self.messages_history) >= 2, "there must more than or equal to 2 messages in history"
        task_messages = self.messages_history.pop() 
        self.history_token_usage.pop()
        response = task_messages[-1]["content"]
        return response

    def _requires_compression(self) -> bool:
        if self.config.compress_threshold and self.history_token_usage:
            current_usage = self.history_token_usage[-1]
            return current_usage.total_tokens > self.config.compress_threshold * self.config.model_max_tokens
        return False

    def _compress_current_message(self) -> None:
        if self.ui_interface:
            try:
                self.ui_interface.display_info("History context too long, compressing...")
            except Exception:
                pass

        current_messages = self.messages_history[-1]
        user_indices = self._get_user_message_indices(current_messages)
        
        if len(user_indices) > 1:
            self._compress_multiple_sessions(current_messages, user_indices)
        elif len(user_indices) == 1:
            self._compress_single_session(current_messages, user_indices[0], 3)
    
    def _get_user_message_indices(self, messages: List) -> List[int]:
        return [i for i, msg in enumerate(messages) if msg.get('role') == Role.USER]
    
    def _compress_multiple_sessions(self, messages: List, user_indices: List[int]) -> None:
        second_oldest_user_index = user_indices[1]

        system_messages = [msg for msg in messages[:second_oldest_user_index] if msg.get('role') == Role.SYSTEM]
        recent_messages = messages[second_oldest_user_index:]

        self.messages_history[-1] = system_messages + self._create_compression_notice(messages) + recent_messages

    def _compress_single_session(self, messages: List, user_index: int, delete_message_num: int) -> None:
        system_messages = [msg for msg in messages[:user_index] if msg.get('role') == Role.SYSTEM]
        
        start_index = min(user_index + 1 + delete_message_num, len(messages))
        user_message = [messages[user_index]] + self._create_compression_notice(messages) + messages[start_index:]

        self.messages_history[-1] = system_messages + user_message

    def _create_compression_notice(self, messages: List) -> List:
        if not messages:
            return []
        
        compression_notice = {
            "role": Role.USER,
            "content": "[Previous conversation history has been compressed to save context window space]"
        }
        return [compression_notice]

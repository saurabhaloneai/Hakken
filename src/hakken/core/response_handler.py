from typing import TYPE_CHECKING, Optional, Tuple, Any

from hakken.core.models import AssistantMessage

if TYPE_CHECKING:
    from hakken.terminal_bridge import UIManager


class ResponseHandler:
    
    def __init__(self, ui_manager: "UIManager"):
        self._ui_manager = ui_manager

    def process_stream(self, stream_generator) -> Tuple[Any, str, Optional[Any]]:
        response_message = None
        full_content = ""
        token_usage = None
        
        iterator = iter(stream_generator)
        
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
            response_message = AssistantMessage(content=full_content)
            
        return response_message, full_content, token_usage

    @staticmethod
    def get_trimmed_content(content) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_value = block.get("text", "")
                    if isinstance(text_value, str):
                        text_parts.append(text_value)
            return " ".join(text_parts).strip()
        return ""

    @staticmethod
    def has_tool_calls(response_message) -> bool:
        return hasattr(response_message, 'tool_calls') and response_message.tool_calls


from typing import Any, Dict
from tools.tool_interface import ToolInterface
from history.conversation_history import CropDirection


class ContextCropper(ToolInterface):
    
    def __init__(self, history_manager=None):
        super().__init__()
        self.history_manager = history_manager

    @staticmethod
    def get_tool_name() -> str:
        return "smart_context_cropper"

    async def act(self, crop_direction: str, crop_amount: int, deleted_messages_summary: str = "", need_user_approve: bool = True, **kwargs) -> Any:
        try:
            if crop_amount <= 0:
                return "Invalid crop amount. It must be positive."
            
            if not self.history_manager:
                return "History manager not available"
            
            direction = CropDirection.TOP if crop_direction.lower() == "top" else CropDirection.BOTTOM
            result = self.history_manager.crop_message(direction, crop_amount)
            return result
        except Exception as e:
            return f"smart_context_cropper run Error: {e}"

    def json_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": self._tool_description(),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "need_user_approve": {
                            "type": "boolean",
                            "description": "Whether the crop messages action requires explicit user approval before execution",
                            "default": True
                        },
                        "crop_direction": {
                            "type": "string",
                            "enum": ["top", "bottom"],
                            "description": "Direction to crop messages. 'top' removes messages from the start (after system message), 'bottom' removes from the end."
                        },
                        "crop_amount": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "Number of messages to remove. Must not exceed the allowed limit for preserving the latest user message."
                        },
                        "deleted_messages_summary": {
                            "type": "string",
                            "description": "Summary of the deleted messages."
                        }
                    },
                    "required": ["need_user_approve", "crop_direction", "crop_amount", "deleted_messages_summary"]
                }
            }
        }
    
    def get_status(self) -> str:
        return "ready"
    
    def _tool_description(self) -> str:
        return """
Crop conversation history from either the top (after system messages) or the bottom, while ensuring the latest user message is never removed.

Before executing smart_context_cropper, follow these steps:
1. Crop Rules
    - Always preserve the latest user message.
    - Top crop → remove the oldest non-system messages that appear after the system message.
    - Bottom crop → remove the most recent messages first.

2. Approval Requirements
    - Always consider the user's current task.
    - If you are certain that the messages to be cropped are unrelated to the user's current task, you may proceed without explicit approval.
    - If there is any uncertainty, request confirmation before cropping.

3. Handling Removed Content
    - If cropped messages contain useful information, provide a concise summary before deletion.
    - Ensure summaries retain any context that might still be relevant to the user's ongoing task.
    - If Nothing useful related in deleted message, than deleted_messages_summary will be empty.
"""
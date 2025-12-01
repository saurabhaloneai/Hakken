from hakken.tools.base import BaseTool
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from hakken.history.manager import HistoryManager


TOOL_DESCRIPTION = """Manually manage conversation context and compression.

Use this tool to:
- Check current context usage (action="status")
- Clear old tool results to free space (action="clear_tools")
- Compress conversation history (action="compress")

The compression uses LLM-based summarization to preserve key decisions and context while removing redundant information.

When to use:
- Context window approaching limit
- Before starting new phase of work
- After extensive tool usage with lots of outputs"""


class ContextCompressionTool(BaseTool):
    def __init__(self, history_manager: Optional["HistoryManager"] = None):
        super().__init__()
        self.history_manager = history_manager
    
    @staticmethod
    def get_tool_name():
        return "compress_context"
    
    async def act(self, action: str = "compress", aggressive: bool = False):
        if not self.history_manager:
            return "Error: History manager not available"
        
        if action == "status":
            context_pct = self.history_manager.current_context_window
            msg_count = len(self.history_manager.messages_history[-1])
            return f"Context: {context_pct}% used, {msg_count} messages in history"
        
        if action == "clear_tools":
            cleared = self.history_manager.clear_old_tool_results(keep_last_n=3)
            return f"Cleared {cleared} old tool results from context"
        
        if action == "compress":
            if aggressive:
                old_threshold = self.history_manager._compress_threshold
                self.history_manager._compress_threshold = 0.5
            
            before_count = len(self.history_manager.messages_history[-1])
            self.history_manager._compress_current_message()
            after_count = len(self.history_manager.messages_history[-1])
            
            if aggressive:
                self.history_manager._compress_threshold = old_threshold
            
            saved = before_count - after_count
            return f"Compression complete. Removed {saved} messages from history."
        
        return f"Unknown action: {action}. Use 'compress', 'clear_tools', or 'status'"
    
    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["compress", "clear_tools", "status"],
                            "description": "Action to perform",
                            "default": "compress"
                        },
                        "aggressive": {
                            "type": "boolean",
                            "description": "For compress action: use more aggressive compression (higher information loss)",
                            "default": False
                        }
                    },
                    "required": []
                }
            }
        }
    
    def get_status(self):
        if not self.history_manager:
            return "not available (no history manager)"
        return "ready"
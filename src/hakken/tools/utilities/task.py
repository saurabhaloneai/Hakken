from typing import TYPE_CHECKING
from hakken.tools.base import BaseTool

if TYPE_CHECKING:
    from hakken.terminal_bridge import UIManager
    from hakken.subagents.manager import SubagentManager


TOOL_DESCRIPTION = """Delegate a complex, multi-step task to a specialized subagent.

Use this tool when you need to:
- Break down a large problem into focused subtasks
- Perform a complex operation that requires multiple steps
- Maintain context isolation for a specific piece of work
- Run tasks that might take significant time or resources

The subagent will:
- Receive the task description
- Plan and execute the necessary steps
- Report back with results
- Maintain its own context and state

Best for:
- Complex refactoring tasks
- Feature implementation with multiple files
- Debugging multi-step issues
- Tasks requiring focused, isolated context

Note: This requires subagent support to be enabled."""


class TaskTool(BaseTool):
    def __init__(self, ui_manager: "UIManager" = None, subagent_manager: "SubagentManager" = None):
        super().__init__()
        self.ui_manager = ui_manager
        self.subagent_manager = subagent_manager
    
    @staticmethod
    def get_tool_name():
        return "task"
    
    async def act(self, task_description):
        if not task_description:
            return "Error: task_description parameter is required"
        
        if not self.subagent_manager:
            return "Error: Subagent manager not available. Task delegation is disabled."
        
        if not self.ui_manager:
            return "Error: UI manager not available. Cannot display task progress."
        
        if hasattr(self.ui_manager, 'send_message'):
            self.ui_manager.send_message({
                'type': 'task_start',
                'description': task_description
            })
        
        result = await self.subagent_manager.run_task(task_description)
        
        if hasattr(self.ui_manager, 'send_message'):
            self.ui_manager.send_message({
                'type': 'task_complete',
                'description': task_description,
                'result': result
            })
        
        return f"Task completed:\n{result}"
    
    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_description": {
                            "type": "string",
                            "description": "Clear, detailed description of the task to delegate to the subagent"
                        }
                    },
                    "required": ["task_description"]
                }
            }
        }
    
    def get_status(self):
        if self.subagent_manager:
            return "ready (subagent available)"
        return "disabled (no subagent manager)"
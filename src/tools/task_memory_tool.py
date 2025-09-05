from typing import Any, Dict
import uuid
from datetime import datetime
from .tool_interface import ToolInterface
from memory.task_memory import TaskMemory, TaskMemoryManager


class TaskMemoryTool(ToolInterface):
    
    def __init__(self):
        super().__init__()
        self.memory_manager = TaskMemoryManager()
        self.current_session = str(uuid.uuid4())[:8]

    @staticmethod
    def get_tool_name() -> str:
        return "task_memory"

    async def act(self, action: str, **kwargs) -> Any:
        if action == "save":
            return await self._save_memory(**kwargs)
        elif action == "recall":
            return await self._recall_context(**kwargs)
        elif action == "similar":
            return await self._find_similar(**kwargs)
        else:
            return f"Unknown action: {action}"

    async def _save_memory(self, **kwargs) -> str:
        task_desc = kwargs.get("description", "Task in progress")
        progress = kwargs.get("progress", {})
        decisions = kwargs.get("decisions", [])
        context = kwargs.get("context", "")
        files = kwargs.get("files_changed", [])
        next_steps = kwargs.get("next_steps", [])
        
        memory = TaskMemory(
            id=f"{self.current_session}_{datetime.now().strftime('%H%M')}",
            timestamp=datetime.now(),
            description=task_desc,
            progress=progress,
            decisions=decisions,
            context=context,
            files_changed=files,
            next_steps=next_steps
        )
        
        if self.memory_manager.save_memory(memory):
            return f"Memory saved: {task_desc}"
        else:
            return "Failed to save memory"

    async def _recall_context(self, **kwargs) -> str:
        days = kwargs.get("days", 3)
        return self.memory_manager.get_context_summary(days)

    async def _find_similar(self, **kwargs) -> str:
        description = kwargs.get("description", "")
        similar_tasks = self.memory_manager.find_similar_tasks(description)
        
        if not similar_tasks:
            return "No similar tasks found"
        
        result = f"Found {len(similar_tasks)} similar tasks:\n"
        for task in similar_tasks:
            result += f"- {task.description} ({task.timestamp.strftime('%m-%d')})\n"
            if task.decisions:
                result += f"  Key decisions: {task.decisions[-1].get('decision', 'N/A')}\n"
        
        return result

    def json_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": "Manage task memory for long-horizon tasks - save progress, recall context, find similar tasks",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["save", "recall", "similar"],
                            "description": "Memory action: save current state, recall recent context, or find similar tasks"
                        },
                        "description": {
                            "type": "string",
                            "description": "Task description or search query"
                        },
                        "progress": {
                            "type": "object",
                            "description": "Current progress data (completion %, milestones, etc.)"
                        },
                        "decisions": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Key decisions made during the task"
                        },
                        "context": {
                            "type": "string",
                            "description": "Current context and situation"
                        },
                        "files_changed": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of files modified during task"
                        },
                        "next_steps": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Planned next steps"
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of days to look back for context recall",
                            "default": 3
                        }
                    },
                    "required": ["action"]
                }
            }
        }
    
    def get_status(self) -> str:
        recent_count = len(self.memory_manager.get_recent_memories(days=7))
        return f"Task Memory: {recent_count} recent entries, session: {self.current_session}"

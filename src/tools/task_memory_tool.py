from typing import Any, Dict
import uuid
from datetime import datetime
from tools.tool_interface import ToolInterface
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
                "description": self._tool_description(),
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
    
    def _tool_description(self) -> str:
        return """
Manage persistent task memory for long-horizon tasks - save progress, recall context, and find similar past work.

This tool provides memory capabilities for complex, multi-session tasks by storing and retrieving contextual information about your work.

Available Actions:
1. save - Store current task state and progress
   - Captures task description, progress data, key decisions
   - Records modified files and planned next steps
   - Associates memory with current session for easy retrieval
   - Creates timestamped entries for chronological tracking

2. recall - Retrieve recent context and progress
   - Fetches summaries of recent work within specified days
   - Helps resume interrupted tasks with full context
   - Default lookback period: 3 days
   - Provides chronological overview of recent activities

3. similar - Find tasks with similar descriptions or context
   - Uses description matching to find related past work
   - Shows previously made decisions and lessons learned
   - Helps avoid repeating research or rediscovering solutions
   - Returns ranked list of similar tasks with key insights

When to Use Task Memory:
- Multi-day or multi-session projects
- Complex tasks with many decision points
- Research tasks where context accumulates over time
- Collaborative work where progress needs to be shared
- Learning from past similar tasks

Save Memory Parameters:
- description: Brief summary of current task
- progress: Structured data about completion status, milestones
- decisions: Array of key decisions made during task execution
- context: Current situation, blockers, insights
- files_changed: List of modified files for tracking impact
- next_steps: Planned actions for task continuation

Memory Management:
- Automatic session tracking with unique identifiers
- Timestamped entries for chronological organization
- Persistent storage across application restarts
- Efficient retrieval based on time ranges and similarity

Best Practices:
- Save memory at key decision points and major milestones
- Include enough context for future sessions to understand state
- Use descriptive task descriptions for better similarity matching
- Regularly recall context when resuming complex tasks
- Search for similar tasks before starting new research
"""

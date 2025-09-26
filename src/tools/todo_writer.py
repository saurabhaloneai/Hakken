import json
import os
from typing import Any, Dict, List
from tools.tool_interface import ToolInterface


class TodoWriteManager(ToolInterface):

    def __init__(self, ui_interface=None):
        super().__init__()
        self.todos = []
        self.ui_interface = ui_interface

    @staticmethod
    def get_tool_name() -> str:
        return "todo_write"

    async def act(self, todos: List[Dict] = None, **kwargs) -> Any:
        if not todos:
            return "No todos provided"
        
       
        if not isinstance(todos, list):
            return f"Error: todos type is wrong. Expected list, got {type(todos).__name__}. todos = {todos}"
        
        for i, todo in enumerate(todos):
            if not isinstance(todo, dict):
                return f"Error: todo item {i} type is wrong. Expected dict, got {type(todo).__name__}. todos = {todos}"
            
            required_fields = ['content', 'status', 'id']
            for field in required_fields:
                if field not in todo:
                    return f"Error: todo item {i} missing required field '{field}'. todos = {todos}"
            
            if todo['status'] not in ['pending', 'in_progress', 'completed']:
                return f"Error: todo item {i} has invalid status '{todo['status']}'. Must be one of: pending, in_progress, completed. todos = {todos}"
        
        self.todos = todos

        # update ui state and display
        if self.ui_interface:
            try:
                self.ui_interface.update_todos(todos)
            except Exception:
                pass
            self.ui_interface.display_todos(todos)

        # persist to repo root as todo.md (manus-style)
        try:
            self._persist_markdown()
        except Exception:
            # non-fatal; still return success for in-memory usage
            pass
        
        return f"Successfully updated todo list with {len(todos)} todos"

    def json_schema(self) -> Dict:
        """Get JSON schema for this tool"""
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": self._tool_description(),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "todos": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "content": {
                                        "type": "string",
                                        "minLength": 1
                                    },
                                    "status": {
                                        "type": "string",
                                        "enum": [
                                            "pending",
                                            "in_progress",
                                            "completed"
                                        ]
                                    },
                                    "id": {
                                        "type": "string"
                                    }
                                },
                                "required": [
                                    "content",
                                    "status",
                                    "id"
                                ],
                                "additionalProperties": False
                            },
                            "description": "The updated todo list"
                        }
                    },
                    "required": [
                        "todos"
                    ],
                    "additionalProperties": False
                }
            }
        }
    
    def get_status(self) -> str:
        if not self.todos:
            return "No todos in memory - no todos have been added yet"
        return json.dumps({"todos": self.todos}, indent=2)

    def _persist_markdown(self) -> None:
        """Write a deterministic, human-readable todo.md at repo root."""
        lines = ["# Project Tasks", ""]
        for todo in self.todos:
            status = todo.get("status", "pending")
            content = todo.get("content", "").strip()
            if status == "completed":
                box = "[x]"
                suffix = ""
            elif status == "in_progress":
                box = "[ ]"
                suffix = " — in progress"
            else:
                box = "[ ]"
                suffix = ""
            lines.append(f"- {box} {content}{suffix}")
        lines.append("")  # trailing newline
        path = os.path.join(os.getcwd(), "todo.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _tool_description(self) -> str:
        return """
Use this tool to create and manage a structured task list for your current coding session. This helps you track progress, organize complex tasks, and demonstrate thoroughness to the user.
It also helps the user understand the progress of the task and overall progress of their requests.

#### When to Use This Tool
Use this tool proactively in these scenarios:

1. Complex multi-step tasks - When a task requires 3 or more distinct steps or actions
2. Non-trivial and complex tasks - Tasks that require careful planning or multiple operations
3. User explicitly requests todo list - When the user directly asks you to use the todo list
4. User provides multiple tasks - When users provide a list of things to be done (numbered or comma-separated)
5. After receiving new instructions - Immediately capture user requirements as todos
6. When you start working on a task - Mark it as in_progress BEFORE beginning work. Ideally you should only have one todo as in_progress at a time
7. After completing a task - Mark it as completed and add any new follow-up tasks discovered during implementation

#### Task States and Management

1. **Task States**: Use these states to track progress:
   - pending: Task not yet started
   - in_progress: Currently working on (limit to ONE task at a time)
   - completed: Task finished successfully

2. **Task Management**:
   - Update task status in real-time as you work
   - Mark tasks complete IMMEDIATELY after finishing (don't batch completions)
   - Only have ONE task in_progress at any time
   - Complete current tasks before starting new ones
   - Remove tasks that are no longer relevant from the list entirely

3. **Task Completion Requirements**:
   - ONLY mark a task as completed when you have FULLY accomplished it
   - If you encounter errors, blockers, or cannot finish, keep the task as in_progress
   - When blocked, create a new task describing what needs to be resolved
   - Never mark a task as completed if:
     - Tests are failing
     - Implementation is partial
     - You encountered unresolved errors
     - You couldn't find necessary files or dependencies
"""

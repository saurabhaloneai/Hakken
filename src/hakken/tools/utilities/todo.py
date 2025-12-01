import json
import os
from typing import TYPE_CHECKING
from hakken.tools.base import BaseTool

if TYPE_CHECKING:
    from hakken.terminal_bridge import UIManager


class TodoTool(BaseTool):
    def __init__(self, ui_manager: "UIManager" = None, todo_file=".hakken_todos.json"):
        super().__init__()
        self.ui_manager = ui_manager
        self.todo_file = todo_file
    
    @staticmethod
    def get_tool_name():
        return "todo_write"
    
    async def act(self, action="list", task=None, task_id=None):
        todos = self._load_todos()
        
        if action == "add":
            if not task:
                return "Error: task parameter required for 'add' action"
            new_id = max([t['id'] for t in todos], default=0) + 1
            new_todo = {
                'id': new_id,
                'task': task,
                'completed': False
            }
            todos.append(new_todo)
            self._save_todos(todos)
            return f"Task added with ID {new_id}: {task}"
        
        elif action == "list":
            if not todos:
                return "No tasks found. Use action='add' to create tasks."
            
            result = "TODO List:\n" + "=" * 60 + "\n"
            pending = [t for t in todos if not t['completed']]
            completed = [t for t in todos if t['completed']]
            
            if pending:
                result += "\n📋 Pending Tasks:\n"
                for todo in pending:
                    result += f"  [{todo['id']}] {todo['task']}\n"
            
            if completed:
                result += "\n✓ Completed Tasks:\n"
                for todo in completed:
                    result += f"  [{todo['id']}] {todo['task']}\n"
            
            result += "\n" + "=" * 60
            result += f"\nTotal: {len(pending)} pending, {len(completed)} completed"
            return result
        
        elif action == "complete":
            if task_id is None:
                return "Error: task_id parameter required for 'complete' action"
            
            for todo in todos:
                if todo['id'] == task_id:
                    if todo['completed']:
                        return f"Task {task_id} is already completed"
                    todo['completed'] = True
                    self._save_todos(todos)
                    return f"Task {task_id} marked as complete: {todo['task']}"
            
            return f"Error: Task {task_id} not found"
        
        elif action == "remove":
            if task_id is None:
                return "Error: task_id parameter required for 'remove' action"
            
            for i, todo in enumerate(todos):
                if todo['id'] == task_id:
                    removed = todos.pop(i)
                    self._save_todos(todos)
                    return f"Task {task_id} removed: {removed['task']}"
            
            return f"Error: Task {task_id} not found"
        
        else:
            return f"Error: Unknown action '{action}'. Valid actions: add, list, complete, remove"
    
    def _load_todos(self):
        if not os.path.exists(self.todo_file):
            return []
        try:
            with open(self.todo_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    
    def _save_todos(self, todos):
        with open(self.todo_file, 'w', encoding='utf-8') as f:
            json.dump(todos, f, indent=2, ensure_ascii=False)
    
    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": """Structured task management for tracking work items.

Use this for task management (what needs to be done):
- Add tasks to work on
- Mark tasks as complete
- List pending and completed tasks
- Remove tasks

This is separate from repository knowledge (use add_memory for that).

Actions:
- add: Create new task (requires 'task' parameter)
- list: Show all tasks (default)
- complete: Mark task done (requires 'task_id')
- remove: Delete task (requires 'task_id')""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "Action to perform",
                            "enum": ["add", "list", "complete", "remove"],
                            "default": "list"
                        },
                        "task": {
                            "type": "string",
                            "description": "Task description (required for 'add' action)"
                        },
                        "task_id": {
                            "type": "integer",
                            "description": "Task ID (required for 'complete' and 'remove' actions)"
                        }
                    },
                    "required": []
                }
            }
        }
    
    def get_status(self):
        todos = self._load_todos()
        pending = len([t for t in todos if not t['completed']])
        return f"ready ({pending} pending tasks)"
import json
import os
from typing import TYPE_CHECKING, List, Dict, Any
from hakken.tools.base import BaseTool

if TYPE_CHECKING:
    from hakken.terminal_bridge import UIManager


TOOL_DESCRIPTION = """Use this tool to create and manage a structured task list for your current coding session. This helps you track progress, organize complex tasks, and demonstrate thoroughness to the user. A todo.md file is automatically created/updated showing real-time progress.

#### When to Use This Tool
Use this tool proactively in these scenarios:

1. Complex multi-step tasks - When a task requires 3 or more distinct steps or actions
2. Non-trivial and complex tasks - Tasks that require careful planning or multiple operations
3. User explicitly requests todo list - When the user directly asks you to use the todo list
4. User provides multiple tasks - When users provide a list of things to be done (numbered or comma-separated)
5. After receiving new instructions - Immediately capture user requirements as todos
6. When you start working on a task - Mark it as in_progress BEFORE beginning work. Ideally you should only have one todo as in_progress at a time
7. After completing a task - Mark it as completed and add any new follow-up tasks discovered during implementation

#### When NOT to Use This Tool

Skip using this tool when:
1. There is only a single, straightforward task
2. The task is trivial and tracking it provides no organizational benefit
3. The task can be completed in less than 3 trivial steps
4. The task is purely conversational or informational

NOTE that you should not use this tool if there is only one trivial task to do. In this case you are better off just doing the task directly.

#### Examples of When to Use the Todo List

<example>
User: I want to add a dark mode toggle to the application settings. Make sure you run the tests and build when you're done!
Assistant: I'll help add a dark mode toggle to your application settings. Let me create a todo list to track this implementation.
*Creates todo list with the following items:*
1. Create dark mode toggle component in Settings page
2. Add dark mode state management (context/store)
3. Implement CSS-in-JS styles for dark theme
4. Update existing components to support theme switching
5. Run tests and build process, addressing any failures or errors that occur
*Begins working on the first task*

<reasoning>
The assistant used the todo list because:
1. Adding dark mode is a multi-step feature requiring UI, state management, and styling changes
2. The user explicitly requested tests and build be run afterward
3. The assistant inferred that tests and build need to pass by adding "Ensure tests and build succeed" as the final task
</reasoning>
</example>

<example>
User: Help me rename the function getCwd to getCurrentWorkingDirectory across my project
Assistant: Let me first search through your codebase to find all occurrences of 'getCwd'.
*Uses grep or search tools to locate all instances of getCwd in the codebase*
Assistant: I've found 15 instances of 'getCwd' across 8 different files. Let me create a todo list to track these changes.
*Creates todo list with specific items for each file that needs updating*

<reasoning>
The assistant used the todo list because:
1. First, the assistant searched to understand the scope of the task
2. Upon finding multiple occurrences across different files, it determined this was a complex task with multiple steps
3. The todo list helps ensure every instance is tracked and updated systematically
4. This approach prevents missing any occurrences and maintains code consistency
</reasoning>
</example>

#### Examples of When NOT to Use the Todo List

<example>
User: How do I print 'Hello World' in Python?
Assistant: In Python, you can print "Hello World" with this simple code: print("Hello World")

<reasoning>
The assistant did not use the todo list because this is a single, trivial task that can be completed in one step.
</reasoning>
</example>

<example>
User: What does the git status command do?
Assistant: The git status command shows the current state of your working directory and staging area.

<reasoning>
The assistant did not use the todo list because this is an informational request with no actual coding task to complete.
</reasoning>
</example>

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

4. **Task Breakdown**:
   - Create specific, actionable items
   - Break complex tasks into smaller, manageable steps
   - Use clear, descriptive task names

When in doubt, use this tool. Being proactive with task management demonstrates attentiveness and ensures you complete all requirements successfully."""


class TodoTool(BaseTool):
    """
    Todo list management tool that writes complete todo state each call.
    Creates and maintains a todo.md file for human-readable progress tracking.
    """
    
    def __init__(self, ui_manager: "UIManager" = None, todo_file=".hakken_todos.json", todo_md_file="todo.md"):
        super().__init__()
        self.ui_manager = ui_manager
        self.todo_file = todo_file
        self.todo_md_file = todo_md_file
        self.todos: List[Dict[str, Any]] = []
    
    @staticmethod
    def get_tool_name():
        return "todo_write"
    
    async def act(self, todos: List[Dict[str, Any]] = None):
        """
        Update the entire todo list with the provided todos.
        Each call replaces the complete todo state.
        """
        if todos is None:
            return "Error: todos parameter is required"
        
        if not isinstance(todos, list):
            return f"Error: todos must be a list, got {type(todos).__name__}"
        
        for i, todo in enumerate(todos):
            if not isinstance(todo, dict):
                return f"Error: todo item {i} must be a dict, got {type(todo).__name__}"
            
            required_fields = ['id', 'content', 'status']
            for field in required_fields:
                if field not in todo:
                    return f"Error: todo item {i} missing required field '{field}'"
            
            valid_statuses = ['pending', 'in_progress', 'completed']
            if todo['status'] not in valid_statuses:
                return f"Error: todo item {i} has invalid status '{todo['status']}'. Must be one of: {', '.join(valid_statuses)}"
        
        self.todos = todos
        self._save_todos(todos)
        self._update_ui(todos)
        
        # Generate summary
        pending = len([t for t in todos if t['status'] == 'pending'])
        in_progress = len([t for t in todos if t['status'] == 'in_progress'])
        completed = len([t for t in todos if t['status'] == 'completed'])
        
        return f"Todo list updated: {len(todos)} total ({pending} pending, {in_progress} in progress, {completed} completed)"
    
    def _load_todos(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.todo_file):
            return []
        try:
            with open(self.todo_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    def _save_todos(self, todos: List[Dict[str, Any]]):
        with open(self.todo_file, 'w', encoding='utf-8') as f:
            json.dump(todos, f, indent=2, ensure_ascii=False)
        
        if len(todos) > 0:
            self._write_todo_md(todos)
        elif os.path.exists(self.todo_md_file):
            os.remove(self.todo_md_file)

    def _write_todo_md(self, todos: List[Dict[str, Any]]):
        from datetime import datetime
        
        pending = [t for t in todos if t.get('status') == 'pending']
        in_progress = [t for t in todos if t.get('status') == 'in_progress']
        completed = [t for t in todos if t.get('status') == 'completed']
        total = len(todos)
        done = len(completed)
        
        lines = [
            "# 📋 Task Progress",
            "",
            f"> **Progress: {done}/{total} completed** {'✅' if done == total and total > 0 else '🔄'}",
            f"> Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            ""
        ]
        
        if in_progress:
            lines.append("## 🔄 In Progress")
            lines.append("")
            for t in in_progress:
                lines.append(f"- [ ] **[{t['id']}]** {t['content']}")
            lines.append("")
        
        if pending:
            lines.append("## ⏳ Pending")
            lines.append("")
            for t in pending:
                lines.append(f"- [ ] **[{t['id']}]** {t['content']}")
            lines.append("")
        
        if completed:
            lines.append("## ✅ Completed")
            lines.append("")
            for t in completed:
                lines.append(f"- [x] ~~**[{t['id']}]** {t['content']}~~")
            lines.append("")
        
        lines.append("---")
        lines.append("*Generated by Hakken Agent*")
        
        with open(self.todo_md_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

    def _update_ui(self, todos: List[Dict[str, Any]]):
        if not self.ui_manager or not hasattr(self.ui_manager, 'display_todos'):
            return
        self.ui_manager.display_todos(todos)
    
    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "todos": {
                            "type": "array",
                            "description": "Complete list of all todos. Each call replaces the entire todo state.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "Unique identifier for the todo"
                                    },
                                    "content": {
                                        "type": "string",
                                        "description": "Task description",
                                        "minLength": 1
                                    },
                                    "status": {
                                        "type": "string",
                                        "description": "Current status of the task",
                                        "enum": ["pending", "in_progress", "completed"]
                                    }
                                },
                                "required": ["id", "content", "status"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["todos"],
                    "additionalProperties": False
                }
            }
        }
    
    def get_status(self):
        todos = self._load_todos()
        if not todos:
            return "ready (no active todos)"
        pending = len([t for t in todos if t.get('status') == 'pending'])
        in_progress = len([t for t in todos if t.get('status') == 'in_progress'])
        completed = len([t for t in todos if t.get('status') == 'completed'])
        return f"ready ({pending} pending, {in_progress} in progress, {completed} completed)"
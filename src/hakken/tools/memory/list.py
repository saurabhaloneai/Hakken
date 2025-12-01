import os
import json
from hakken.tools.base import BaseTool


TOOL_DESCRIPTION = """Retrieve all repository-specific knowledge entries from persistent storage.

Use this tool to:
- Review stored knowledge about the codebase architecture
- Check important configuration details and conventions
- Recall key dependencies and their purposes
- Access non-obvious implementation details
- Remember project-specific terminology

This is separate from task management (use todo_write for tasks). This retrieves knowledge about the repository itself."""


class ListMemoriesTool(BaseTool):
    def __init__(self, memory_file=".hakken_memories.json"):
        super().__init__()
        self.memory_file = memory_file
    
    @staticmethod
    def get_tool_name():
        return "list_memories"
    
    async def act(self):
        if not os.path.exists(self.memory_file):
            return "No knowledge entries found. Use add_memory to store repository-specific knowledge."
        
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                memories = json.load(f)
        except json.JSONDecodeError:
            return "Error: Knowledge file is corrupted. No entries available."
        
        if not memories:
            return "No knowledge entries found. Use add_memory to store repository-specific knowledge."
        
        result = "Repository Knowledge:\n" + "-" * 50 + "\n"
        for i, memory in enumerate(memories, 1):
            result += f"{i}. {memory}\n"
        result += "-" * 50 + f"\nTotal: {len(memories)} entries"
        
        return result
    
    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    
    def get_status(self):
        return "ready"
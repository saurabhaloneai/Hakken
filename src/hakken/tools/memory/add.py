from hakken.tools.base import BaseTool


class AddMemoryTool(BaseTool):
    def __init__(self, memory_file=".hakken_memories.json"):
        super().__init__()
        self.memory_file = memory_file
    
    @staticmethod
    def get_tool_name():
        return "add_memory"
    
    async def act(self, entry):
        if not entry:
            return "Error: entry is required"
        
        from hakken.utils.json_store import append_to_json_list
        
        error, count = append_to_json_list(self.memory_file, entry)
        if error:
            return f"Error: {error}"
        
        return f"Knowledge entry added successfully. Total entries: {count}"
    
    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": """Store repository-specific knowledge that persists across sessions.

Use this tool to save important information about THIS repository:
- Architecture decisions and design patterns used
- Important configuration details or conventions
- Key dependencies and their purposes
- Non-obvious implementation details
- Project-specific terminology or concepts

This is separate from task management (use todo_write for tasks). Use this for knowledge that should be remembered about the codebase itself.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entry": {
                            "type": "string",
                            "description": "Repository-specific knowledge to store. Be specific about what aspect of the codebase this relates to."
                        }
                    },
                    "required": ["entry"]
                }
            }
        }
    
    def get_status(self):
        return "ready"
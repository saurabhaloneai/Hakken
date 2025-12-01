import os
from hakken.tools.base import BaseTool


TOOL_DESCRIPTION = """Lists all files and subdirectories within a specified directory.

Use this to:
- Explore project structure
- Find files before reading or editing them
- Understand directory organization
- Verify files exist before operating on them

Returns:
- Name of each item (file or directory)
- Type indicator ([FILE] or [DIR])
- Total count of items

Results are sorted alphabetically. For very large directories (>100 items), 
output is truncated with a count of remaining items."""


class ListDirTool(BaseTool):
    def __init__(self):
        super().__init__()

    @staticmethod
    def get_tool_name():
        return "list_dir"

    async def act(self, directory_path):
        if not directory_path:
            return "Error: directory_path is required"
        
        if not os.path.isabs(directory_path):
            return f"Error: directory_path must be an absolute path. Got: {directory_path}"
            
        if not os.path.exists(directory_path):
            return f"Error: Directory not found: {directory_path}"

        if not os.path.isdir(directory_path):
            return f"Error: Path is not a directory: {directory_path}"

        items = os.listdir(directory_path)
        result = []
        for item in items:
            item_path = os.path.join(directory_path, item)
            is_dir = os.path.isdir(item_path)
            type_str = "DIR" if is_dir else "FILE"
            result.append(f"[{type_str}] {item}")
        
        sorted_result = sorted(result)
        
        # Truncate if too many items
        if len(sorted_result) > 100:
            output = "\n".join(sorted_result[:100])
            output += f"\n... and {len(sorted_result) - 100} more items (directory too large, showing first 100)"
        else:
            output = "\n".join(sorted_result)
        
        return f"Directory: {directory_path}\nTotal items: {len(items)}\n{output}"

    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory_path": {
                            "type": "string",
                            "description": "The absolute path to the directory."
                        }
                    },
                    "required": ["directory_path"]
                }
            }
        }

    def get_status(self):
        return "ready"

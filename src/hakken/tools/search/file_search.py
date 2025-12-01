import os
from pathlib import Path
from hakken.tools.base import BaseTool


class FileSearchTool(BaseTool):
    def __init__(self):
        super().__init__()
    
    @staticmethod
    def get_tool_name():
        return "file_search"
    
    async def act(self, directory, pattern="*", max_depth=None):
        if not directory:
            return "Error: directory parameter is required"
        
        if not os.path.isabs(directory):
            return f"Error: directory must be an absolute path. Got: {directory}"
        
        if not os.path.exists(directory):
            return f"Error: Directory not found: {directory}"
        
        if not os.path.isdir(directory):
            return f"Error: Path is not a directory: {directory}"
        
        matches = []
        start_depth = directory.count(os.sep)
        
        for root, dirs, files in os.walk(directory):
            # Check depth limit
            if max_depth is not None:
                current_depth = root.count(os.sep) - start_depth
                if current_depth > max_depth:
                    dirs[:] = []  # Don't descend further
                    continue
            
            # Match files
            path_obj = Path(root)
            for file in files:
                file_path = path_obj / file
                if file_path.match(pattern):
                    matches.append(str(file_path))
        
        if not matches:
            return f"No files found matching pattern '{pattern}' in {directory}"
        
        # Format results
        result = f"Found {len(matches)} file(s) matching '{pattern}':\n"
        result += "-" * 50 + "\n"
        for match in matches[:50]:  # Limit to 50 results
            result += f"{match}\n"
        
        if len(matches) > 50:
            result += f"\n... and {len(matches) - 50} more files"
        
        return result
    
    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": """Search for files by name pattern in a directory tree.

Use this to find files when you know (part of) the filename but not the exact location:
- Find all Python files: pattern='*.py'
- Find test files: pattern='*test*.py'  
- Find config files: pattern='config.*'
- Find specific file: pattern='setup.py'

Supports glob patterns with wildcards (* and ?). Results are limited to 50 files to avoid overwhelming output.

Unlike grep_search which searches file contents, this searches file names.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Absolute path to the directory to search in"
                        },
                        "pattern": {
                            "type": "string",
                            "description": "File name pattern with wildcards (e.g., '*.py', 'test_*.js')",
                            "default": "*"
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum directory depth to search (None for unlimited)"
                        }
                    },
                    "required": ["directory"]
                }
            }
        }
    
    def get_status(self):
        return "ready"
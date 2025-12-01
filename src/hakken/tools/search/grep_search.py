import os
import re
from hakken.tools.base import BaseTool


TOOL_DESCRIPTION = """Search for text patterns in file contents (like grep command).

Use this to find code or text when you know what you're looking for:
- Find function calls: pattern='function_name('
- Find class definitions: pattern='class.*MyClass'
- Find imports: pattern='import.*module_name'
- Find TODO comments: pattern='TODO'

Supports regular expressions for complex patterns. Shows matching lines with file paths and line numbers.

Unlike file_search which searches file names, this searches file contents.
Unlike semantic_search which understands meaning, this does exact text/regex matching."""


class GrepSearchTool(BaseTool):
    def __init__(self):
        super().__init__()
    
    @staticmethod
    def get_tool_name():
        return "grep_search"
    
    async def act(self, pattern, path, file_pattern="*", case_sensitive=True, max_results=100):
        if not pattern:
            return "Error: pattern parameter is required"
        
        if not path:
            return "Error: path parameter is required"
        
        if not os.path.isabs(path):
            return f"Error: path must be absolute. Got: {path}"
        
        if not os.path.exists(path):
            return f"Error: Path not found: {path}"
        
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)
        except re.error as e:
            return f"Error: Invalid regex pattern: {str(e)}"
        
        matches = []
        files_searched = 0
        
        def search_file(file_path):
            nonlocal files_searched
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    files_searched += 1
                    for line_num, line in enumerate(f, 1):
                        if len(matches) >= max_results:
                            return
                        if regex.search(line):
                            matches.append({
                                'file': file_path,
                                'line_num': line_num,
                                'content': line.rstrip()
                            })
            except (UnicodeDecodeError, IOError):
                pass
        
        if os.path.isfile(path):
            search_file(path)
        else:
            # Search directory
            from pathlib import Path
            for root, _, files in os.walk(path):
                for file in files:
                    if len(matches) >= max_results:
                        break
                    file_path = Path(root) / file
                    if file_path.match(file_pattern):
                        search_file(str(file_path))
        
        if not matches:
            return f"No matches found for pattern '{pattern}' (searched {files_searched} files)"
        
        # Format results
        result = f"Found {len(matches)} match(es) for '{pattern}' ({files_searched} files searched):\n"
        result += "=" * 60 + "\n"
        
        current_file = None
        for match in matches:
            if match['file'] != current_file:
                current_file = match['file']
                result += f"\n{current_file}:\n"
            result += f"  Line {match['line_num']}: {match['content']}\n"
        
        if len(matches) >= max_results:
            result += f"\n(Results limited to {max_results} matches)"
        
        return result
    
    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Text or regex pattern to search for in file contents"
                        },
                        "path": {
                            "type": "string",
                            "description": "Absolute path to file or directory to search in"
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "Filter which files to search (e.g., '*.py', '*.js')",
                            "default": "*"
                        },
                        "case_sensitive": {
                            "type": "boolean",
                            "description": "Whether the search should be case-sensitive",
                            "default": True
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of matching lines to return",
                            "default": 100
                        }
                    },
                    "required": ["pattern", "path"]
                }
            }
        }
    
    def get_status(self):
        return "ready"
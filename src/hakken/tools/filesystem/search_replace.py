import os
from hakken.tools.base import BaseTool

class SearchReplaceTool(BaseTool):
    def __init__(self):
        super().__init__()

    @staticmethod
    def get_tool_name():
        return "search_replace"

    async def act(self, file_path, search_string, replace_string, count=None):
        if not file_path:
            return "Error: file_path is required"
        
        if not os.path.isabs(file_path):
            return f"Error: file_path must be an absolute path. Got: {file_path}"
            
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if search_string not in content:
            return f"Error: Search string '{search_string}' not found in file: {file_path}. Verify the exact string exists or use grep_search to find similar patterns."

        if count is not None:
            new_content = content.replace(search_string, replace_string, count)
            occurrences = count
        else:
            occurrences = content.count(search_string)
            new_content = content.replace(search_string, replace_string)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return f"Successfully replaced {occurrences} occurrence(s) in file: {file_path}"

    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": """Performs find-and-replace operations on file content using exact string matching.

This is ideal for:
- Renaming variables, functions, or classes across a file
- Updating configuration values
- Replacing repeated text patterns

By default, replaces ALL occurrences. Use the 'count' parameter to limit replacements.
For example, count=1 replaces only the first occurrence.

Important:
- Uses exact string matching (not regex)
- Search is case-sensitive
- File must exist (cannot create new files)
- Reports an error if the search_string is not found in the file

Returns a success message indicating how many replacements were made.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The absolute path to the file."
                        },
                        "search_string": {
                            "type": "string",
                            "description": "The string to search for."
                        },
                        "replace_string": {
                            "type": "string",
                            "description": "The string to replace with."
                        },
                        "count": {
                            "type": "integer",
                            "description": "Optional number of occurrences to replace. If omitted, replaces all."
                        }
                    },
                    "required": ["file_path", "search_string", "replace_string"]
                }
            }
        }

    def get_status(self):
        return "ready"

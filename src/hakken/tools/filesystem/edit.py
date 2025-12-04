import os
from hakken.tools.base import BaseTool
from hakken.utils.files import write_file_content, replace_file_lines, validate_absolute_path


TOOL_DESCRIPTION = """Creates a new file or modifies an existing file's content.

This tool supports three modes:
1. **Create new file**: Provide file_path and content (without line numbers)
2. **Full file overwrite**: Provide file_path and content (existing file, no line numbers)  
3. **Line-based edit**: Provide file_path, content, start_line, and optionally end_line

Line-based editing:
- Lines are 1-indexed (first line is 1, not 0)
- Replaces lines [start_line, end_line] inclusive with new content
- If only start_line provided, replaces from start_line to end of file
- Cannot specify line numbers when creating a new file

Always ensure you have read the file first before making line-based edits to avoid mistakes.
The tool will create parent directories automatically if they don't exist."""


class EditFileTool(BaseTool):
    def __init__(self):
        super().__init__()

    @staticmethod
    def get_tool_name():
        return "edit_file"

    async def act(self, file_path, content, start_line=None, end_line=None):
        if not file_path:
            return "Error: file_path is required"
        
        error = validate_absolute_path(file_path)
        if error:
            return f"Error: {error}"
            
        if not content and start_line is None:
            return "Error: content is required"

        if not os.path.exists(file_path):
            if start_line is not None or end_line is not None:
                return f"Error: Cannot specify line numbers for a new file. To create {file_path}, provide only file_path and content."
            
            error = write_file_content(file_path, content)
            if error:
                return f"Error: {error}"
            return f"Successfully created new file: {file_path}"

        if start_line is None and end_line is None:
            error = write_file_content(file_path, content, create_dirs=False)
            if error:
                return f"Error: {error}"
            return f"Successfully overwrote file: {file_path}"

        if start_line is None:
            start_line = 1
        
        error = replace_file_lines(file_path, content, start_line, end_line)
        if error:
            return f"Error: {error}"
        
        return f"Successfully updated file: {file_path} (lines {start_line}-{end_line or 'EOF'})"

    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The absolute path to the file."
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write."
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "The starting line number for replacement (1-indexed). If omitted with end_line, overwrites the file."
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "The ending line number for replacement (1-indexed)."
                        }
                    },
                    "required": ["file_path", "content"]
                }
            }
        }

    def get_status(self):
        return "ready"

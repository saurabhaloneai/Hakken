from hakken.tools.base import BaseTool
from hakken.utils.files import read_file_lines


class ReadFileTool(BaseTool):
    def __init__(self):
        super().__init__()

    @staticmethod
    def get_tool_name():
        return "read_file"

    async def act(self, file_path, start_line=1, end_line=None):
        error, lines, total = read_file_lines(file_path, start_line, end_line)
        
        if error:
            return f"Error: {error}"
        
        content = "".join(lines)
        actual_end = start_line + len(lines) - 1 if lines else start_line
        
        return f"""File: {file_path}
Lines: {start_line}-{actual_end} (Total: {total})
--------------------------------------------------
{content}
--------------------------------------------------"""

    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": """Reads the content of a text file from the filesystem. 

Use this to examine source code, configuration files, logs, or any text-based content. 
You can read the entire file or specify a line range (1-indexed) to focus on specific sections.

When to use line ranges:
- Reading large files: Start with a small range to understand structure
- Debugging: Focus on specific functions or sections
- Performance: Avoid loading thousands of lines when you only need a snippet

The response includes the file path, line range, total lines, and the actual content.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The absolute path to the file to read."
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "The line number to start reading from (1-indexed). Default is 1.",
                            "default": 1
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "The line number to stop reading at (1-indexed). Default is end of file."
                        }
                    },
                    "required": ["file_path"]
                }
            }
        }

    def get_status(self):
        return "ready"

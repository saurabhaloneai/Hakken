import os
from hakken.tools.base import BaseTool


TOOL_DESCRIPTION = """Permanently deletes a file from the filesystem.

⚠️ WARNING: This action is permanent and cannot be undone.

Use cases:
- Removing temporary or generated files
- Cleaning up test artifacts
- Deleting obsolete code files

The tool will:
- Verify the file exists before attempting deletion
- Confirm the path is a file (not a directory)
- Require an absolute path for safety

Returns a success message if the file was deleted successfully."""


class DeleteFileTool(BaseTool):
    def __init__(self):
        super().__init__()

    @staticmethod
    def get_tool_name():
        return "delete_file"

    async def act(self, file_path):
        if not file_path:
            return "Error: file_path is required"
        
        if not os.path.isabs(file_path):
            return f"Error: file_path must be an absolute path. Got: {file_path}"
            
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        if not os.path.isfile(file_path):
            return f"Error: Path is not a file (use appropriate tool for directories): {file_path}"

        os.remove(file_path)
        return f"Successfully deleted file: {file_path}"

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
                            "description": "The absolute path to the file to delete."
                        }
                    },
                    "required": ["file_path"]
                }
            }
        }

    def get_status(self):
        return "ready"

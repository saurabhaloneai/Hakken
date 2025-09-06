from pathlib import Path
from typing import Dict, Any
from .tool_interface import ToolInterface


class FileEditor(ToolInterface):
    """Simple file editing tool"""
    
    @staticmethod
    def get_tool_name() -> str:
        return "edit_file"

    def json_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "edit_file",
                "description": "Edit file contents by replacing text",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to edit"
                        },
                        "old_text": {
                            "type": "string",
                            "description": "Text to replace"
                        },
                        "new_text": {
                            "type": "string",
                            "description": "New text to insert"
                        }
                    },
                    "required": ["file_path", "old_text", "new_text"]
                }
            }
        }

    def get_status(self) -> str:
        return "ready"

    async def act(self, file_path: str, old_text: str, new_text: str) -> Dict[str, Any]:
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {"error": f"File not found: {file_path}"}
            
            # Read file
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if old_text exists
            if old_text not in content:
                return {"error": f"Text not found in file: {old_text[:50]}..."}
            
            # Replace text
            new_content = content.replace(old_text, new_text)
            
            # Write back
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return {
                "file_path": str(path),
                "message": "File edited successfully",
                "changes": f"Replaced '{old_text[:30]}...' with '{new_text[:30]}...'"
            }
            
        except Exception as e:
            return {"error": f"Edit error: {str(e)}"}

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
                "description": self._tool_description(),
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
    
    def _tool_description(self) -> str:
        return """
Edit file contents by performing precise text replacement operations.

This tool allows you to make targeted edits to existing files by replacing specific text patterns with new content.

Usage Guidelines:
1. File Path: Provide the full path to the file you want to edit
2. Old Text: The exact text you want to replace (must match exactly)
3. New Text: The replacement text to insert

Requirements:
- The target file must exist
- The old_text must be found exactly in the file
- The replacement is performed on all occurrences of old_text

Safety Features:
- Validates file existence before attempting edits
- Confirms old_text exists before making changes
- Provides clear error messages for failed operations
- Preserves file encoding (UTF-8)

Best Practices:
1. Read the file first to understand its current content
2. Use unique text patterns for old_text to avoid unintended replacements
3. Be precise with whitespace, indentation, and line breaks
4. Test with small changes first for complex edits

Output:
- Returns success confirmation with change summary
- Shows truncated preview of what was replaced
- Includes file path for verification

Use Cases:
- Fix bugs by replacing problematic code
- Update configuration values
- Modify function implementations
- Correct text content in files
"""

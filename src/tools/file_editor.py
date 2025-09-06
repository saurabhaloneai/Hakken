from pathlib import Path
from typing import Dict, Any, Optional
from .tool_interface import ToolInterface, ToolResult


class FileEditor(ToolInterface):
    
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
                        },
                        "max_replacements": {
                            "type": "integer",
                            "description": "Maximum number of replacements to perform (optional, default: unlimited)"
                        }
                    },
                    "required": ["file_path", "old_text", "new_text"]
                }
            }
        }

    def get_status(self) -> str:
        return "ready"

    async def act(self, file_path: str, old_text: str, new_text: str, max_replacements: Optional[int] = None) -> Dict[str, Any]:
        try:
            path = Path(file_path)
            
            if not path.exists():
                return ToolResult(
                    status="error",
                    error=f"File not found: {file_path}"
                ).__dict__
            
            # Read file
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if old_text exists
            if old_text not in content:
                return ToolResult(
                    status="error",
                    error=f"Text not found in file: {old_text[:50]}..."
                ).__dict__
            
            # Count occurrences before replacement
            occurrence_count = content.count(old_text)
            
            # Handle max_replacements constraint
            if max_replacements is not None and max_replacements > 0:
                # Replace up to max_replacements occurrences
                new_content = content
                replacements_made = 0
                while replacements_made < max_replacements and old_text in new_content:
                    new_content = new_content.replace(old_text, new_text, 1)
                    replacements_made += 1
                actual_replacements = replacements_made
            else:
                # Replace all occurrences (original behavior)
                new_content = content.replace(old_text, new_text)
                actual_replacements = occurrence_count
            
            # Write back
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return ToolResult(
                status="success",
                data={
                    "file_path": str(path),
                    "message": "File edited successfully",
                    "changes": f"Replaced '{old_text[:30]}...' with '{new_text[:30]}...'"
                },
                metadata={
                    "total_occurrences": occurrence_count,
                    "replacements_made": actual_replacements,
                    "max_replacements_requested": max_replacements
                }
            ).__dict__
            
        except Exception as e:
            return ToolResult(
                status="error",
                error=f"Edit error: {str(e)}"
            ).__dict__
    
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

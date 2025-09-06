from pathlib import Path
from typing import Optional, Dict, Any
from .tool_interface import ToolInterface


class FileReader(ToolInterface):
    """Simple file reader with line numbers"""
    
    @staticmethod
    def get_tool_name() -> str:
        return "read_file"

    def json_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read file contents with line numbers",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to read"
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "Starting line number (optional)"
                        },
                        "end_line": {
                            "type": "integer", 
                            "description": "Ending line number (optional)"
                        }
                    },
                    "required": ["file_path"]
                }
            }
        }

    def get_status(self) -> str:
        return "ready"

    async def act(self, file_path: str, start_line: Optional[int] = None, 
                 end_line: Optional[int] = None) -> Dict[str, Any]:
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {"error": f"File not found: {file_path}"}
            
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Apply line range if specified
            if start_line or end_line:
                start_idx = (start_line - 1) if start_line else 0
                end_idx = end_line if end_line else len(lines)
                lines = lines[start_idx:end_idx]
                line_offset = start_idx
            else:
                line_offset = 0
            
            # Format with line numbers
            formatted_lines = []
            for i, line in enumerate(lines):
                line_num = line_offset + i + 1
                clean_line = line.rstrip('\n\r')
                formatted_lines.append(f"{line_num:6d}|{clean_line}")
            
            return {
                "content": '\n'.join(formatted_lines),
                "file_path": str(path),
                "total_lines": len(lines)
            }
            
        except Exception as e:
            return {"error": f"Error reading file: {str(e)}"}

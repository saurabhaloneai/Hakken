import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from .tool_interface import ToolInterface


class GrepSearch(ToolInterface):
    """Simple grep-like search tool"""
    
    @staticmethod
    def get_tool_name() -> str:
        return "grep_search"

    def json_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "grep_search",
                "description": "Search for text patterns in files",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Text pattern to search for"
                        },
                        "path": {
                            "type": "string", 
                            "description": "Directory or file path to search (default: current directory)",
                            "default": "."
                        },
                        "file_extension": {
                            "type": "string",
                            "description": "File extension to search (e.g., '.py', '.js')"
                        }
                    },
                    "required": ["pattern"]
                }
            }
        }

    def get_status(self) -> str:
        return "ready"

    async def act(self, pattern: str, path: str = ".", 
                 file_extension: Optional[str] = None) -> Dict[str, Any]:
        try:
            search_path = Path(path)
            if not search_path.exists():
                return {"error": f"Path does not exist: {path}"}
            
            results = []
            
            # Get files to search
            if search_path.is_file():
                files = [search_path]
            else:
                files = []
                for file_path in search_path.rglob("*"):
                    if file_path.is_file():
                        # Skip common ignore patterns
                        if any(ignore in str(file_path) for ignore in ['.git', '__pycache__', 'node_modules']):
                            continue
                        # Filter by extension if specified
                        if file_extension and not file_path.name.endswith(file_extension):
                            continue
                        files.append(file_path)
            
            # Search in files
            for file_path in files[:50]:  # Limit to 50 files
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern.lower() in line.lower():
                                results.append({
                                    "file": str(file_path),
                                    "line": line_num,
                                    "content": line.strip()
                                })
                                if len(results) >= 20:  # Limit results
                                    break
                except:
                    continue  # Skip files we can't read
                
                if len(results) >= 20:
                    break
            
            return {
                "pattern": pattern,
                "results": results,
                "total_matches": len(results)
            }
            
        except Exception as e:
            return {"error": f"Search error: {str(e)}"}

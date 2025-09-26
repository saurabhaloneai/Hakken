from pathlib import Path
from typing import Dict, Any, Optional
from tools.tool_interface import ToolInterface, ToolResult


class GrepSearch(ToolInterface):
     
    @staticmethod
    def get_tool_name() -> str:
        return "grep_search"

    def json_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "grep_search",
                "description": self._tool_description(),
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
                return ToolResult(
                    status="error",
                    error=f"Path does not exist: {path}"
                ).__dict__
            
            results = []
            file_limit = 50
            match_limit = 20
            files_processed = 0
            files_truncated = False
            matches_truncated = False
            
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
            
            # Check if we're truncating files
            if len(files) > file_limit:
                files_truncated = True
                files = files[:file_limit]
            
            # Search in files
            for file_path in files:
                files_processed += 1
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern.lower() in line.lower():
                                results.append({
                                    "file": str(file_path),
                                    "line": line_num,
                                    "content": line.strip()
                                })
                                if len(results) >= match_limit:
                                    matches_truncated = True
                                    break
                except Exception:
                    continue
                
                if len(results) >= match_limit:
                    break
            
            return ToolResult(
                status="success",
                data={
                    "pattern": pattern,
                    "results": results,
                    "total_matches": len(results),
                    "files_processed": files_processed
                },
                metadata={
                    "truncated": files_truncated or matches_truncated,
                    "files_truncated": files_truncated,
                    "matches_truncated": matches_truncated,
                    "file_limit": file_limit,
                    "match_limit": match_limit
                }
            ).__dict__
            
        except Exception as e:
            return ToolResult(
                status="error",
                error=f"Search error: {str(e)}"
            ).__dict__
    
    def _tool_description(self) -> str:
        return """
Search for text patterns across files in a directory tree with intelligent filtering and result limiting.

This tool provides powerful text search capabilities similar to grep, with built-in optimizations for code exploration.

Search Parameters:
1. pattern (required): Text pattern to search for
   - Case-insensitive matching
   - Searches within file contents line by line
   - Simple string matching (not regex)

2. path (optional): Directory or file path to search
   - Default: current directory (".")
   - Can specify a single file for targeted search
   - Recursively searches subdirectories

3. file_extension (optional): Filter by file type
   - Example: ".py" for Python files, ".js" for JavaScript
   - Helps narrow search scope for faster results

Smart Features:
- Auto-ignores common non-source directories (.git, __pycache__, node_modules)
- Limits search to 50 files maximum for performance
- Limits results to 20 matches to prevent overwhelming output
- Gracefully handles binary files and encoding issues

Output Format:
- Returns array of matches with file path, line number, and content
- Each match shows the exact line where pattern was found
- Includes total match count for quick assessment

Performance Optimizations:
- Stops searching after reaching result limits
- Skips common ignore patterns automatically
- Uses efficient file traversal for large directories

Use Cases:
- Find function definitions across a codebase
- Locate configuration values in config files
- Search for error messages or log patterns
- Discover usage of specific variables or imports
- Code review and debugging assistance

Best Practices:
- Use specific file extensions for faster, targeted searches
- Use descriptive patterns to get relevant results
- Check result count - if maxed out, consider narrowing the search
"""

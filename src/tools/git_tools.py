import subprocess
from typing import Dict, Any
from .tool_interface import ToolInterface


class GitTools(ToolInterface):
    """Simple Git operations"""
    
    @staticmethod
    def get_tool_name() -> str:
        return "git_status"

    def json_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "git_status",
                "description": self._tool_description(),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Git command: 'status', 'diff', 'log'",
                            "enum": ["status", "diff", "log"]
                        }
                    },
                    "required": ["command"]
                }
            }
        }

    def get_status(self) -> str:
        return "ready"

    async def act(self, command: str) -> Dict[str, Any]:
        try:
            if command == "status":
                result = subprocess.run(['git', 'status', '--porcelain'], 
                                      capture_output=True, text=True)
            elif command == "diff":
                result = subprocess.run(['git', 'diff'], 
                                      capture_output=True, text=True)
            elif command == "log":
                result = subprocess.run(['git', 'log', '--oneline', '-10'], 
                                      capture_output=True, text=True)
            else:
                return {"error": f"Unknown git command: {command}"}
            
            if result.returncode == 0:
                return {
                    "command": f"git {command}",
                    "output": result.stdout
                }
            else:
                return {"error": f"Git command failed: {result.stderr}"}
                
        except Exception as e:
            return {"error": f"Git error: {str(e)}"}
    
    def _tool_description(self) -> str:
        return """
Perform basic Git operations to understand repository state and recent changes.

This tool provides access to essential Git commands for repository analysis and status checking.

Available Commands:
1. status - Show the working tree status
   - Displays modified, added, and deleted files
   - Uses --porcelain format for clean output
   - Perfect for understanding current changes

2. diff - Show changes between commits and working tree
   - Displays line-by-line differences for modified files
   - Shows what has been changed but not yet committed
   - Useful for reviewing modifications before commit

3. log - Show recent commit history
   - Displays the last 10 commits in one-line format
   - Shows commit hash and commit message
   - Helps understand recent development activity

Usage Guidelines:
- Use 'status' to get an overview of current repository state
- Use 'diff' to see detailed changes in modified files
- Use 'log' to understand recent commit history
- All commands work from the current working directory

Error Handling:
- Gracefully handles non-git directories
- Provides clear error messages for failed operations
- Returns both command output and error information

Security:
- Only performs read-only Git operations
- Does not modify repository state
- Safe to use for repository inspection
"""

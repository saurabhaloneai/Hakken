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
                "description": "Get git status and basic git operations",
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

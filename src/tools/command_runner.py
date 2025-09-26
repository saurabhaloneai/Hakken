
import subprocess
from typing import Any, Dict
from tools.tool_interface import ToolInterface


class CommandRunner(ToolInterface):
    
    def __init__(self):
        super().__init__()
        self.status = "ready"

    @staticmethod
    def get_tool_name() -> str:
        return "cmd_runner"

    async def act(self, command: str = "", timeout: int = 30, need_user_approve: bool = True, **kwargs) -> Any:
        if not command:
            return "No command provided"
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                if result.stdout.strip():
                    return result.stdout
                else:
                    return "Command executed successfully and no return"
            else:
                return f"Error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "Command timed out"
        except Exception as e:
            self.status = "error"
            return f"cmd_runner Exception: {str(e)}"

    def json_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": self._tool_description(),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "need_user_approve": {
                            "type": "boolean",
                            "description": "Whether the command requires explicit user approval before execution",
                            "default": True
                        },
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Maximum number of seconds to wait for the command to finish",
                            "default": 30
                        }
                    },
                    "required": ["need_user_approve", "command"]
                }
            }
        }
    
    def get_status(self) -> str:
        return self.status
    
    def _tool_description(self) -> str:
        return """
Executes a given bash command in a persistent shell session with optional timeout, user approval, and security measures.

Before using this tool, prefer dedicated tools:
- Read files: use the read_file tool (do not use `cat` here)
- Edit files: use the edit_file tool (do not use `sed` here)
- Search code/text: use the grep_search tool (avoid shell `grep`)

Use this tool for:
- Listing/inspecting directories (e.g., `ls -la`, `tree`)
- Running tests/linters/formatters and project commands (pytest, ruff, black, npm, etc.)
- Git/pip/system utilities and other shell tasks not covered by dedicated tools

1. Security Check:
   - Treat commands that can modify or delete data as dangerous (e.g., rm, sudo, chmod 777, chown -R, dd, mkfs, kill -9 -1, shutdown/reboot)
   - If potentially dangerous or impactful, you MUST set need_user_approve=true

2. Directory Verification:
   - If the command will create new directories or files, verify parents first (e.g., use `ls` to confirm the intended parent exists)

3. Usage notes:
  - The command and need_user_approve arguments are required.
  - timeout is in seconds (default 30; practical max ~120).
  - Prefer absolute paths; avoid `cd` unless the user explicitly requests it.
""" 
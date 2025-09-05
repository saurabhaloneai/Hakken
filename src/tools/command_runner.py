
import subprocess
from typing import Any, Dict
from .tool_interface import ToolInterface


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

Before executing the command, please follow these steps:
1. Security Check:
   - Always check if the command is potentially dangerous (e.g., rm, sudo, chmod 777, format, del, etc.)
   - If the command is dangerous or could cause system damage/data loss, you MUST set need_user_approve=true

2. Directory Verification:
   - If the command will create new directories or files, first use the ls command to verify the parent directory exists and is the correct location
   - For example, before running "mkdir foo/bar", first use ls to check that "foo" exists and is the intended parent directory

3. Read File Command:
   - When you need to read a file for the first time, always use `cat -n <file>` to display the contents with line numbers (default max 2000 lines)

4. Edit File Command:
   - Before updating any file, you must read the file content in the current conversation first
   - When updating content in an existing file, always use sed for replacement except when the updated content is very large:
     Example: `sed -i "start_line,end_line c new_content" <file>`
   - When inserting content into an existing file, use sed for insertion:
     Example: `sed -i "insert_line_number a insert_content" <file>`
   - When searching within files, always use grep:
     Example: `grep "search_pattern" <file>`
   - Before editing a file, use sed to preview the specific lines with their line numbers if you are unsure of the exact range. Make sure it's the code you actually want to update.
     Example: sed -n "start_line,end_line p" <file>

Usage notes:
  - The command and need_user_approve arguments are required.
  - You can specify an optional timeout in milliseconds (up to 120 seconds). If not specified, commands will timeout after 30 seconds.
  - Try to maintain your current working directory throughout the session by using absolute paths and avoiding usage of `cd`. You may use `cd` if the User explicitly requests it.
"""
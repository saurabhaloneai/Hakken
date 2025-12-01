import subprocess
from hakken.tools.base import BaseTool


class CmdRunner(BaseTool):
    def __init__(self):
        super().__init__()

    @staticmethod
    def get_tool_name():
        return "cmd_runner"

    async def act(self, command="", timeout=30):
        if not command:
            return "Error: No command provided. Provide a shell command to execute."
        
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
                    return "Command executed successfully (no output)"
            else:
                return f"Command failed with exit code {result.returncode}:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout} seconds. Consider increasing the timeout parameter or simplifying the command."

    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": """Executes shell commands in the workspace with timeout and approval controls.

⚠️ Security: Always set need_user_approve=true for potentially dangerous commands (rm, sudo, chmod 777, etc.)

This tool supports:
- Running bash/shell commands with configurable timeout (default 30s, max 120s)
- Capturing stdout/stderr output
- Detecting command failures via exit codes

Best practices:
- Use absolute paths to avoid working directory issues
- For file operations, prefer dedicated file tools (read_file, edit_file, etc.) when available
- For git operations, verify changes with git status/diff before committing
- Batch independent commands when possible for better performance

Returns command output on success, or error message with exit code on failure.""",
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
    
    def get_status(self):
        return ""
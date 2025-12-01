import subprocess
import os
from hakken.tools.base import BaseTool


class GitLogTool(BaseTool):
    def __init__(self):
        super().__init__()
    
    @staticmethod
    def get_tool_name():
        return "git_log"
    
    async def act(self, repository_path=None, max_count=10, file_path=None):
        if repository_path and not os.path.isabs(repository_path):
            return f"Error: repository_path must be absolute. Got: {repository_path}"
        
        cwd = repository_path if repository_path else os.getcwd()
        
        if not os.path.exists(cwd):
            return f"Error: Path not found: {cwd}"
        
        cmd = [
            'git', 'log',
            f'-{max_count}',
            '--pretty=format:%h - %an, %ar : %s',
            '--date=relative'
        ]
        
        if file_path:
            cmd.extend(['--', file_path])
        
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0:
            if not result.stdout.strip():
                return "No commits found."
            return f"Recent commits:\n{result.stdout}"
        else:
            return f"Error: {result.stderr}"
    
    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": """View git commit history.

Shows recent commits with:
- Commit hash (short form)
- Author name
- Relative time (e.g., "2 hours ago")
- Commit message

Use this to:
- See recent changes to the codebase
- Find who made specific changes
- Review commit history before pushing
- Track changes to specific files""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repository_path": {
                            "type": "string",
                            "description": "Absolute path to git repository (default: current directory)"
                        },
                        "max_count": {
                            "type": "integer",
                            "description": "Maximum number of commits to show",
                            "default": 10
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Show log for specific file only (relative to repository root)"
                        }
                    },
                    "required": []
                }
            }
        }
    
    def get_status(self):
        return "ready"
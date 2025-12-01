import subprocess
import os
from hakken.tools.base import BaseTool


TOOL_DESCRIPTION = """Push commits to a remote git repository.

⚠️ Warning: This modifies remote repository state.

Use this to:
- Share commits with team members
- Back up local commits to remote
- Deploy changes to production branch

Best practices:
- Review commits with git_log before pushing
- Avoid force push unless absolutely necessary
- Ensure you're on the correct branch
- Pull latest changes before pushing to avoid conflicts"""


class GitPushTool(BaseTool):
    def __init__(self):
        super().__init__()
    
    @staticmethod
    def get_tool_name():
        return "git_push"
    
    async def act(self, repository_path=None, remote="origin", branch=None, force=False):
        if repository_path and not os.path.isabs(repository_path):
            return f"Error: repository_path must be absolute. Got: {repository_path}"
        
        cwd = repository_path if repository_path else os.getcwd()
        
        if not os.path.exists(cwd):
            return f"Error: Path not found: {cwd}"
        
        cmd = ['git', 'push']
        if force:
            cmd.append('--force')
        cmd.append(remote)
        if branch:
            cmd.append(branch)
        
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            output = result.stdout if result.stdout else result.stderr
            return f"Push successful:\n{output}"
        else:
            return f"Error pushing to remote: {result.stderr}"
    
    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repository_path": {
                            "type": "string",
                            "description": "Absolute path to git repository (default: current directory)"
                        },
                        "remote": {
                            "type": "string",
                            "description": "Name of remote to push to",
                            "default": "origin"
                        },
                        "branch": {
                            "type": "string",
                            "description": "Branch to push (default: current branch)"
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force push (overwrites remote history - use with extreme caution)",
                            "default": False
                        }
                    },
                    "required": []
                }
            }
        }
    
    def get_status(self):
        return "ready"
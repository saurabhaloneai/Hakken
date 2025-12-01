from hakken.tools.base import BaseTool


class GitCommitTool(BaseTool):
    def __init__(self):
        super().__init__()
    
    @staticmethod
    def get_tool_name():
        return "git_commit"
    
    async def act(self, message, repository_path=None, add_all=False):
        from hakken.utils.git import git_commit, run_git_command
        
        if not message:
            return "Error: message parameter is required"
        
        if add_all:
            success, output = run_git_command(['add', '-A'], repository_path)
            if not success:
                return f"Error staging changes: {output}"
        
        success, output = git_commit(message, repository_path)
        
        if success:
            return f"Commit successful:\n{output}"
        else:
            if "nothing to commit" in output:
                return "No changes to commit. Use git_status to see current state."
            return f"Error creating commit: {output}"
    
    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": """Create a git commit with a message.

Best practices:
- Use clear, descriptive commit messages
- Review changes with git_diff before committing
- Use add_all=true to stage all changes, or stage specific files first
- Check git_status to see what will be committed

The commit message should describe what changed and why.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Commit message describing the changes"
                        },
                        "repository_path": {
                            "type": "string",
                            "description": "Absolute path to git repository (default: current directory)"
                        },
                        "add_all": {
                            "type": "boolean",
                            "description": "Stage all changes before committing (equivalent to git add -A)",
                            "default": False
                        }
                    },
                    "required": ["message"]
                }
            }
        }
    
    def get_status(self):
        return "ready"
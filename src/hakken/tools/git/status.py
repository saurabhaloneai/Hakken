from hakken.tools.base import BaseTool


class GitStatusTool(BaseTool):
    def __init__(self):
        super().__init__()
    
    @staticmethod
    def get_tool_name():
        return "git_status"
    
    async def act(self, repository_path=None):
        from hakken.utils.git import git_status
        
        success, output = git_status(repository_path)
        return output
    
    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": """Check the status of a git repository.

Shows:
- Current branch
- Modified files
- Untracked files
- Staged changes
- Files ready to commit

Use this before making commits to see what changes are present.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repository_path": {
                            "type": "string",
                            "description": "Absolute path to git repository (default: current directory)"
                        }
                    },
                    "required": []
                }
            }
        }
    
    def get_status(self):
        return "ready"
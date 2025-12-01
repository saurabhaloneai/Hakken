from hakken.tools.base import BaseTool


TOOL_DESCRIPTION = """View git diffs to see what changed.

Shows line-by-line changes:
- Lines added (+ prefix)
- Lines removed (- prefix)
- Context lines (no prefix)

Options:
- View all unstaged changes (default)
- View staged changes (staged=true)
- View changes for specific file (file_path)

Use this before committing to review your changes."""


class GitDiffTool(BaseTool):
    @staticmethod
    def get_tool_name():
        return "git_diff"
    
    async def act(self, repository_path=None, file_path=None, staged=False):
        from hakken.utils.git import run_git_command
        
        cmd = ['diff']
        if staged:
            cmd.append('--staged')
        if file_path:
            cmd.append(file_path)
        
        success, output = run_git_command(cmd, repository_path)
        
        if not success:
            return f"Error: {output}"
        
        if not output.strip():
            return "No changes to show."
        
        return output
    
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
                        "file_path": {
                            "type": "string",
                            "description": "Specific file to show diff for (relative to repository root)"
                        },
                        "staged": {
                            "type": "boolean",
                            "description": "Show staged changes instead of unstaged changes",
                            "default": False
                        }
                    },
                    "required": []
                }
            }
        }
    
    def get_status(self):
        return "ready"
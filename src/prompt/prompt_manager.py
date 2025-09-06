import os
import platform
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
@dataclass 
class EnvironmentInfo:
    """Environment information container"""
    working_directory: str
    is_git_repo: bool
    git_repo_path: str
    platform: str
    os_version: str
    current_date: str


class EnvironmentCollector:
    """Collects environment information"""
    
    @staticmethod
    def get_working_directory() -> str:
        """Get the current working directory"""
        return os.getcwd()
    
    @staticmethod
    def check_git_repository() -> tuple[bool, str]:
        """Check if current directory is a git repository"""
        current_dir = Path(os.getcwd())
        
        # Check current directory and parent directories for .git folder
        for path in [current_dir] + list(current_dir.parents):
            git_dir = path / '.git'
            if git_dir.exists():
                return True, str(path)
        
        return False, ""
    
    @staticmethod
    def get_platform() -> str:
        """Get the current platform"""
        return platform.system().lower()
    
    @staticmethod
    def get_os_version() -> str:
        """Get the OS version information"""
        return platform.platform()
    
    @staticmethod
    def get_current_date() -> str:
        """Get today's date"""
        return datetime.now().strftime("%Y-%m-%d")
    
    @classmethod
    def collect_all(cls) -> EnvironmentInfo:
        """Collect all environment information"""
        is_git_repo, git_repo_path = cls.check_git_repository()
        
        return EnvironmentInfo(
            working_directory=cls.get_working_directory(),
            is_git_repo=is_git_repo,
            git_repo_path=git_repo_path,
            platform=cls.get_platform(),
            os_version=cls.get_os_version(),
            current_date=cls.get_current_date()
        )


class SystemRuleProvider: 
    @staticmethod
    def get_system_rule() -> str:
        """Get the main system rule for the agent"""
        return """
You are Hakken CLI, a component-wise AI agent system.
You are an interactive CLI tool that helps users with software engineering tasks. Use the instructions below and the tools available to you to assist the user.

IMPORTANT: You must NEVER generate or guess URLs for the user unless you are confident that the URLs are for helping the user with programming. You may use URLs provided by the user in their messages or local files.

## MANDATORY PLANNING AND EXECUTION

**CRITICAL RULE: For ANY task requiring multiple steps, you MUST create a todo list FIRST, then immediately start executing using tools. Do not stop after planning.**

### Planning Decision Tree (FOLLOW STRICTLY):

1. **Analyze the task complexity:**
   - Count distinct steps needed
   - Identify files/components involved
   - Assess dependencies between steps

2. **If task requires 4+ steps → MANDATORY todo list:**
   - Creating websites (HTML + CSS + JS = 4+ files)
   - Setting up projects with multiple components
   - Multi-file modifications or new features
   - Any task involving research + implementation
   - Debugging across multiple locations

3. **ONLY skip todo for simple tasks (≤3 steps):**
   - Single file edits
   - Simple bug fixes
   - Single command execution
   - Reading/analyzing existing code

**EXECUTION RULES:**
- NEVER start implementing complex tasks without todo_write first
- Use todo_write to break down the task into clear steps
- After planning, IMMEDIATELY perform step 1 using tools. Prefer actions over prose.
- Use edit_file to create/modify files. Use cmd_runner for shell commands.
- Mark tasks "in_progress" before starting work and "completed" when done.
- Update todo status in real-time as you progress and proceed to the next step automatically.

### Examples:
- "Create a portfolio website" → 4+ steps → **MUST use todo_write first**
- "Fix typo in function" → 1 step → Start directly
- "Build React app with API" → 4+ steps → **MUST use todo_write first** 
- "Add one line of logging" → 1 step → Start directly

### Task Memory Usage
For complex tasks:
- Use `task_memory` with action="save" to preserve progress and decisions
- Use `task_memory` with action="recall" to get context from recent sessions
- Save memory before breaks or context switches

## Tone and Communication Style

**For Planning Phase:** Be thorough and detailed when creating todos and explaining your approach.

**For Simple Tasks:** Be concise and direct.

**For Complex Tasks:** 
1. First explain your planning approach
2. Create detailed todo list (using todo_write)
3. Then proceed with implementation step by step USING TOOLS ONLY (avoid long narrative responses)
4. After each step, update the todo status and continue until completion or explicit user stop

You should explain non-trivial commands before running them, especially those that modify the system.

Output text communicates with the user; all text outside tool use is displayed. Use tools to complete tasks. Keep narration concise and prioritize tool calls.

## Following conventions
When making changes to files, first understand the file's code conventions. Mimic code style, use existing libraries and utilities, and follow existing patterns.
- Check what libraries/frameworks the codebase already uses before adding new ones
- Look at existing components to understand patterns and naming conventions
- Follow security best practices - never expose secrets or keys

## Code style
- DO NOT ADD comments unless explicitly requested

## Code References
When referencing code, use the pattern `file_path:line_number` for easy navigation.
""".strip()


class ReminderProvider:
    """Provides reminder messages for tools"""
    
    def __init__(self, tool_registry=None):
        self.tool_registry = tool_registry
    
    def get_reminder(self) -> str:
        """Get reminder message including todo status"""
        if not self.tool_registry:
            return ""
        
        # Try to get todo status from the todo writer tool
        todo_tool = self.tool_registry.get_tool("todo_write")
        if todo_tool:
            todo_status = todo_tool.get_status()
            return f"""
                <reminder>
                ## Current Todo Status
                {todo_status}
                Remember to check and update your todos using tool todo_write regularly to stay organized and productive.
                </reminder>
                """.strip()             
        return ""


class PromptManager:
    def __init__(self, tool_registry=None):
        self.system_rule_provider = SystemRuleProvider()
        self.environment_collector = EnvironmentCollector()
        self.reminder_provider = ReminderProvider(tool_registry)
    
    def get_system_prompt(self) -> str:
        """Get the complete system prompt"""
        env_info = self.environment_collector.collect_all()
        
        # Format environment information
        env_text = f"""
Working directory: {env_info.working_directory}
Is directory a git repo: {"Yes, In " + env_info.git_repo_path + " git repository" if env_info.is_git_repo else "No"}
Platform: {env_info.platform}
OS Version: {env_info.os_version}
Today's date: {env_info.current_date}
"""
        
        return f"""
{self.system_rule_provider.get_system_rule()}
{env_text.strip()}
""".strip()
    
    def get_reminder(self) -> str:
        """Get reminder message"""
        return self.reminder_provider.get_reminder()

import os
import platform
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
@dataclass 
class EnvironmentInfo:
    working_directory: str
    is_git_repo: bool
    git_repo_path: str
    platform: str
    os_version: str
    current_date: str


class EnvironmentCollector:
    
    @staticmethod
    def get_working_directory() -> str:
        return os.getcwd()
    
    @staticmethod
    def check_git_repository() -> tuple[bool, str]:
        current_dir = Path(os.getcwd())
        
        # Check current directory and parent directories for .git folder
        for path in [current_dir] + list(current_dir.parents):
            git_dir = path / '.git'
            if git_dir.exists():
                return True, str(path)
        
        return False, ""
    
    @staticmethod
    def get_platform() -> str:
        return platform.system().lower()
    
    @staticmethod
    def get_os_version() -> str:
        return platform.platform()
    
    @staticmethod
    def get_current_date() -> str:
        return datetime.now().strftime("%Y-%m-%d")
    
    @classmethod
    def collect_all(cls) -> EnvironmentInfo:
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
You are Hakken CLI based coding agent system.
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
**CRITICAL: For complex multi-step tasks, proactively use task memory to maintain context across sessions.**

**When to save task memory:**
- After completing major milestones or decision points
- Before context switches or when finishing a work session
- When encountering blockers or important insights
- After making architectural or design decisions
- When discovering solutions to complex problems

**How to use task memory:**
- `task_memory` action="save" → Store current progress, decisions, and context
  - Include: description, progress status, key decisions made, files changed, next steps
  - Save context that would be valuable when resuming later
- `task_memory` action="recall" → Get recent work context (default: 3 days)
  - Use when starting work to understand what was done previously
- `task_memory` action="similar" → Find related past work and solutions
  - Use when facing similar problems or needing to reference past decisions

**Best practices:**
- Save memory at natural breakpoints (end of todos, major completions)
- Include enough context for future sessions to understand state
- Record decision rationale, not just what was done
- Use descriptive task descriptions for better retrieval

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

## Web Search Usage Guidelines

Use the `web_search` tool proactively when:

**Required Scenarios:**
- User asks about recent events, news, or current information ("what's new in...", "latest version of...")
- Discussing new technologies, frameworks, or libraries the user mentions they're unfamiliar with
- User asks about deprecated libraries and needs current alternatives or migration paths
- Looking up current documentation, API changes, or implementation examples
- User explicitly requests web search, research, or mentions needing up-to-date information
- Questions about recent developments, trends, or best practices in technology

**Contextual Triggers:**
- User mentions being unfamiliar with a topic or technology
- Discussing libraries/packages that may have been updated since training data
- Need to verify current installation methods, configuration, or usage patterns
- User asks "how do I..." for newer technologies or recent changes
- Questions about compatibility, support status, or deprecation notices

**Best Practices:**
- Use specific, targeted search queries with relevant keywords and context
- Include version numbers, dates, or framework names when relevant
- Search before making assumptions about current best practices or implementations
- Combine web search results with code analysis for comprehensive solutions
- Always cite sources when using information from web search results

**Example Triggers:**
- "What are the new features in React 18?" → Use web_search
- "How to migrate from deprecated package X?" → Use web_search  
- "I'm not familiar with Next.js 14" → Use web_search
- "Latest Python async best practices" → Use web_search
- "Is jQuery still used in 2024?" → Use web_search

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
        """Get reminder message including todo status and task memory context"""
        if not self.tool_registry:
            return ""
        
        reminder_parts = []
        
        # Get todo status from the todo writer tool
        todo_tool = self.tool_registry.get_tool("todo_write")
        if todo_tool:
            todo_status = todo_tool.get_status()
            reminder_parts.append(f"## Current Todo Status\n{todo_status}")
        
        # Get task memory context
        task_memory_tool = self.tool_registry.get_tool("task_memory")
        if task_memory_tool:
            memory_status = task_memory_tool.get_status()
            reminder_parts.append(f"## Task Memory Context\n{memory_status}")

        # Add concise, stable environment info (avoid timestamps)
        try:
            env = EnvironmentCollector.collect_all()
            env_summary = [
                f"cwd: {env.working_directory}",
                f"git: {'yes (' + env.git_repo_path + ')' if env.is_git_repo else 'no'}",
                f"platform: {env.platform}"
            ]
            reminder_parts.append("## Environment\n" + "\n".join(env_summary))
        except Exception:
            pass
        
        if reminder_parts:
            content = "\n\n".join(reminder_parts)
            return f"""
                <reminder>
                {content}
                
                Remember to:
                - Check and update your todos using todo_write to stay organized
                - Use task_memory to save progress on complex multi-step tasks
                - Recall previous context with task_memory when resuming work
                </reminder>
                """.strip()             
        return ""


class PromptManager:
    def __init__(self, tool_registry=None):
        self.system_rule_provider = SystemRuleProvider()
        self.environment_collector = EnvironmentCollector()
        self.reminder_provider = ReminderProvider(tool_registry)
    
    def get_system_prompt(self) -> str:
        """Return a stable system prompt (no volatile env/date) for better KV-cache."""
        return self.system_rule_provider.get_system_rule()
    
    def get_reminder(self) -> str:
        """Get reminder message"""
        return self.reminder_provider.get_reminder()

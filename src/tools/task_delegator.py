
from typing import Any, Dict
from .tool_interface import ToolInterface


class SubagentManager:
    
    def __init__(self):
        self._system_prompt_map = {}
        self._initialize_default_agents()
    
    def _initialize_default_agents(self):
        general_purpose_prompt = """
You are an agent for Hakken, a component-wise AI agent system. 
Given the user's message, you should use the tools available to complete the task. 
Do what has been asked; nothing more, nothing less. 
When you complete the task simply respond with a detailed writeup.

Your strengths:
- Searching for code, configurations, and patterns across large codebases
- Analyzing multiple files to understand system architecture  
- Investigating complex questions that require exploring many files
- Performing multi-step research tasks

Guidelines:
- For file searches: Use Grep or Glob when you need to search broadly. Use Read when you know the specific file path.
- For analysis: Start broad and narrow down. Use multiple search strategies if the first doesn't yield results.
- Be thorough: Check multiple locations, consider different naming conventions, look for related files.
- NEVER create files unless they're absolutely necessary for achieving your goal. ALWAYS prefer editing an existing file to creating a new one.
- NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested.
- In your final response always share relevant file names and code snippets. Any file paths you return in your response MUST be absolute. Do NOT use relative paths.
- For clear communication, avoid using emojis.

Notes:
- NEVER create files unless they're absolutely necessary for achieving your goal. ALWAYS prefer editing an existing file to creating a new one.
- NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
- In your final response always share relevant file names and code snippets. Any file paths you return in your response MUST be absolute. Do NOT use relative paths.
- For clear communication with the user the assistant MUST avoid using emojis.
"""
        
        code_specialist_prompt = """
You are a specialized code analysis agent for Hakken.
Your role is to analyze, debug, and optimize code with deep technical expertise.

Your strengths:
- Code review and bug detection
- Performance optimization suggestions
- Architecture analysis and refactoring recommendations
- Security vulnerability identification
- Best practices enforcement

Guidelines:
- Always provide specific file paths and line numbers
- Explain the reasoning behind your recommendations
- Focus on code quality, maintainability, and performance
- Suggest concrete improvements with examples
- Be thorough in your analysis but concise in explanations
"""

        self._system_prompt_map['general'] = general_purpose_prompt
        self._system_prompt_map['code_specialist'] = code_specialist_prompt
    
    def get_agent_prompt(self, agent_type: str) -> str:
        return self._system_prompt_map.get(agent_type, self._system_prompt_map['general'])
    
    def list_agents(self) -> list:
        return list(self._system_prompt_map.keys())


class TaskDelegator(ToolInterface):
    
    def __init__(self, ui_interface, conversation_agent):
        super().__init__()
        self.ui_interface = ui_interface
        self.conversation_agent = conversation_agent
        self.subagent_manager = SubagentManager()

    @staticmethod
    def get_tool_name() -> str:
        return "delegate_task"

    async def act(self, task_description: str, agent_type: str = "general", **kwargs) -> Any:
        try:
            system_prompt = self.subagent_manager.get_agent_prompt(agent_type)
            
            self.ui_interface.print_info(f"Delegating task to {agent_type} agent...")
            
            result = await self.conversation_agent.start_task(system_prompt, task_description)
            
            return {
                "agent_type": agent_type,
                "task": task_description,
                "result": result,
                "status": "completed"
            }
            
        except Exception as e:
            return {
                "agent_type": agent_type,
                "task": task_description,
                "error": str(e),
                "status": "failed"
            }

    def json_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": "Delegate complex tasks to specialized sub-agents with specific expertise",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_description": {
                            "type": "string",
                            "description": "Detailed description of the task to delegate"
                        },
                        "agent_type": {
                            "type": "string",
                            "enum": ["general", "code_specialist"],
                            "description": "Type of specialized agent to use",
                            "default": "general"
                        }
                    },
                    "required": ["task_description"]
                }
            }
        }
    
    def get_status(self) -> str:
        agents = self.subagent_manager.list_agents()
        return f"Task Delegator: {len(agents)} agents available ({', '.join(agents)})"
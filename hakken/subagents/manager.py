"""
Manager for handling multiple sub-agents.
"""

from typing import Dict
from .subagent import SubAgent
from .models import SubAgentConfig


class SubAgentManager:
    def __init__(self, parent_agent):
        self.parent = parent_agent
        self.subagents: Dict[str, SubAgent] = {}
    
    def register_subagent(self, config: SubAgentConfig):
        subagent = SubAgent(config, self.parent)
        self.subagents[config.name] = subagent
    
    def call_subagent(self, name: str, task: str, context: Dict = None) -> str:
        if name not in self.subagents:
            return f"Sub-agent '{name}' not found. Available: {list(self.subagents.keys())}"
        
        subagent = self.subagents[name]
        return subagent.execute(task, context)
    
    def get_subagent_descriptions(self) -> str:
        descriptions = []
        for name, agent in self.subagents.items():
            descriptions.append(f"- {name}: {agent.description}")
        return "\n".join(descriptions) if descriptions else "No specialized sub-agents configured"
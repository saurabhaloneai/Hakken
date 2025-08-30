"""
Factory function for creating DeepAgent instances.
"""

from typing import List, Dict, Callable
from .core.agent import DeepAgent


def create_deep_agent(tools: List[Callable] = None, instructions: str = "",
                     subagents: List[Dict] = None, api_key: str = None, 
                     model: str = "claude-sonnet-4-20250514") -> DeepAgent:
    """
    Create a deep agent with planning and sub-agent capabilities.
    
    Args:
        tools: List of custom tool functions
        instructions: Custom instructions for the agent
        subagents: List of custom sub-agent configurations  
        api_key: Anthropic API key
        model: Claude model to use
        
    Returns:
        DeepAgent instance with performance optimizations:
        - KV-cache optimization for 10x cost reduction
        - Error learning and context preservation
        - Smart memory management with file system
        - Progress recitation for attention management
        - Template variation to avoid few-shot ruts
    """
    return DeepAgent(
        tools=tools, 
        instructions=instructions, 
        subagents=subagents,
        api_key=api_key, 
        model=model
    )
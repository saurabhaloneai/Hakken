"""
Individual sub-agent implementation.
"""

import json
from typing import Dict, List
from .models import SubAgentConfig


class SubAgent:
    def __init__(self, config: SubAgentConfig, parent_agent):
        self.name = config.name
        self.description = config.description
        self.prompt = config.prompt
        self.allowed_tools = config.tools
        self.parent = parent_agent
    
    def execute(self, task: str, context: Dict = None) -> str:
        # Build sub-agent specific prompt
        full_prompt = f"""{self.prompt}

CURRENT TASK: {task}

CONTEXT: {json.dumps(context or {}, indent=2)}

Execute this task using your specialized capabilities. Be focused and thorough."""

        # Get available tools for this sub-agent
        available_tools = self._get_available_tools()
        
        # Execute task with LLM
        messages = [
            {"role": "user", "content": task}
        ]
        
        import time
        import random
        from anthropic import APIError
        
        # Retry logic for API calls
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = self.parent.client.messages.create(
                    model=self.parent.model,
                    max_tokens=8000,
                    system=full_prompt,
                    messages=messages,
                    tools=available_tools
                )
                break
            except APIError as e:
                if attempt == max_retries - 1:
                    print(f"Subagent API error after {max_retries} attempts: {e}")
                    raise
                
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"Subagent API error (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
        
        # Process response and tool calls
        return self._process_subagent_response(response, state=context)
    
    def _get_available_tools(self) -> List[Dict]:
        all_tools = self.parent.tool_registry.get_tool_schemas()
        
        if self.allowed_tools is None:
            return all_tools
        
        return [tool for tool in all_tools if tool["name"] in self.allowed_tools]
    
    def _process_subagent_response(self, response, state=None) -> str:
        results = []
        
        for content_block in response.content:
            if hasattr(content_block, 'type'):
                if content_block.type == 'text':
                    results.append(content_block.text)
                elif content_block.type == 'tool_use':
                    try:
                        tool_result = self.parent.tool_registry.execute(
                            content_block.name,
                            content_block.input
                        )
                        results.append(f"✅ [{content_block.name}] {tool_result}")
                    except Exception as e:
                        # IMPROVEMENT 3: Keep errors in sub-agent context too
                        error_msg = f"❌ [{content_block.name}] FAILED: {str(e)}"
                        results.append(error_msg)
        
        return "\n".join(results)
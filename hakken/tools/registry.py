"""
Tool registry for managing and executing tools.
"""

from typing import Dict, List, Any
from .models import Tool


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool):
        self.tools[tool.name] = tool
    
    def execute(self, name: str, args: Dict[str, Any]) -> Any:
        if name not in self.tools:
            raise ValueError(f"Tool {name} not found")
        return self.tools[name].function(**args)
    
    def get_tool_schemas(self) -> List[Dict]:
        schemas = []
        # IMPROVEMENT 6: Deterministic tool ordering for KV-cache
        sorted_tools = sorted(self.tools.items(), key=lambda x: x[0])
        
        for tool_name, tool in sorted_tools:
            schema = {
                "name": tool.name,
                "description": tool.description,
                "input_schema": {
                    "type": "object",
                    "properties": tool.parameters,
                    "required": tool.required_params
                }
            }
            schemas.append(schema)
        return schemas
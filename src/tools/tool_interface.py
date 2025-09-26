
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Literal, Optional
from dataclasses import dataclass


@dataclass
class ToolResult:
    status: Literal["success", "error"]
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ToolInterface(ABC):
    
    def __init__(self):
        pass

    @staticmethod
    @abstractmethod
    def get_tool_name() -> str:
        pass

    @abstractmethod
    async def act(self, **kwargs) -> Any:
        pass

    @abstractmethod
    def json_schema(self) -> Dict:
        pass

    @abstractmethod
    def get_status(self) -> str:
        pass


class ToolRegistry:
    
    def __init__(self):
        self.tools: Dict[str, ToolInterface] = {}
    
    def register_tool(self, tool_instance: ToolInterface) -> None:
        tool_name = tool_instance.get_tool_name()
        self.tools[tool_name] = tool_instance
    
    def get_tool(self, tool_name: str) -> ToolInterface:
        return self.tools.get(tool_name)
    
    def get_all_tools(self) -> Dict[str, ToolInterface]:
        return self.tools.copy()

    def _normalize_schema(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self._normalize_schema(obj[k]) for k in sorted(obj.keys())}
        if isinstance(obj, list):
            return [self._normalize_schema(v) for v in obj]
        return obj
    
    def get_tools_description(self) -> List[Dict]:
        descriptions = []
        for tool_name, tool_instance in sorted(self.tools.items(), key=lambda kv: kv[0]):
            raw_schema = tool_instance.json_schema()
            normalized = self._normalize_schema(raw_schema)
            descriptions.append(normalized)
        return descriptions
    
    async def run_tool(self, tool_name: str, **kwargs) -> Any:
        tool = self.tools.get(tool_name)
        if not tool:
            return "Tool not found"
        
        try:
            return await tool.act(**kwargs)
        except Exception as e:
            return f"Error occurred while running tool '{tool_name}': {str(e)}"
    
    def get_tool_status(self, tool_name: str) -> str:
        tool = self.tools.get(tool_name)
        if tool:
            return tool.get_status()
        return "Tool not found"

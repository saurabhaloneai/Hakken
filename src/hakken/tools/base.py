from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type


class BaseTool(ABC):
    def __init__(self):
        pass

    @staticmethod
    @abstractmethod
    def get_tool_name() -> str:
        pass
    
    @classmethod
    def get_input_model(cls) -> Optional[Type]:
        return None
    
    @classmethod
    def get_output_model(cls) -> Optional[Type]:
        return None

    @abstractmethod
    def json_schema(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def act(self, **kwargs) -> Any:
        pass

    def get_status(self) -> str:
        return ""
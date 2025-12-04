from typing import Optional, Any
from pydantic import BaseModel


class AssistantMessage(BaseModel):
    content: str
    role: str = "assistant"
    tool_calls: Optional[Any] = None

    class Config:
        arbitrary_types_allowed = True


class ErrorMessage(BaseModel):
    content: str
    role: str = "assistant"
    tool_calls: Optional[Any] = None

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_error(cls, error_msg: str) -> "ErrorMessage":
        return cls(
            content=f"Sorry, I encountered a technical problem: {error_msg}"
        )

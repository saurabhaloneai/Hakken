from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    metadata: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

def system_message(content: str) -> Message:
    return Message(role="system", content=content)

def user_message(content: str) -> Message:
    return Message(role="user", content=content)

def assistant_message(content: str) -> Message:
    return Message(role="assistant", content=content)

def tool_message(content: str) -> Message:
    return Message(role="tool", content=content)
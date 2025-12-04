from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class Todo(BaseModel):
    id: str
    content: str
    status: Literal["pending", "in_progress", "completed"] = "pending"


class AgentState(BaseModel):
    mode: Literal["idle", "running", "blocked", "task"] = "idle"
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    total_cost: float = 0.0
    context_window_percent: float = 0.0
    todos: List[Todo] = Field(default_factory=list)
    current_task_id: Optional[str] = None

    model_config = {"frozen": False}

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentState":
        return cls.model_validate(data)

    def with_mode(self, mode: Literal["idle", "running", "blocked", "task"]) -> "AgentState":
        return self.model_copy(update={"mode": mode})

    def with_message(self, message: Dict[str, Any]) -> "AgentState":
        return self.model_copy(update={"messages": self.messages + [message]})

    def with_token_usage(self, usage: TokenUsage) -> "AgentState":
        return self.model_copy(update={"token_usage": usage})

    def with_cost(self, cost: float) -> "AgentState":
        return self.model_copy(update={"total_cost": cost})

    def with_context_window(self, percent: float) -> "AgentState":
        return self.model_copy(update={"context_window_percent": percent})

    def with_todos(self, todos: List[Todo]) -> "AgentState":
        return self.model_copy(update={"todos": todos})

    def with_task(self, task_id: Optional[str]) -> "AgentState":
        return self.model_copy(update={"current_task_id": task_id})


from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Tracks token consumption for API calls."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class Todo(BaseModel):
    """Represents a single todo item."""
    id: str
    content: str
    status: Literal["pending", "in_progress", "completed"] = "pending"


class AgentState(BaseModel):
    """
    Central state container for the Hakken agent.
    
    All agent state should be tracked here and imported from this module.
    This provides a single source of truth for the agent's current state.
    """
    # Agent execution mode
    mode: Literal["idle", "running", "blocked", "task"] = "idle"
    
    # Conversation history
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Token tracking
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    
    # Cost tracking (in USD)
    total_cost: float = 0.0
    
    # Context window usage (percentage, 0-100)
    context_window_percent: float = 0.0
    
    # Todo list for task tracking
    todos: List[Todo] = Field(default_factory=list)
    
    # Current task ID if in task mode
    current_task_id: Optional[str] = None

    model_config = {"frozen": False}

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentState":
        """Create state from dictionary."""
        return cls.model_validate(data)

    # Immutable update methods (return new state)
    def with_mode(self, mode: Literal["idle", "running", "blocked", "task"]) -> "AgentState":
        """Return new state with updated mode."""
        return self.model_copy(update={"mode": mode})

    def with_message(self, message: Dict[str, Any]) -> "AgentState":
        """Return new state with new message appended."""
        return self.model_copy(update={"messages": self.messages + [message]})

    def with_token_usage(self, usage: TokenUsage) -> "AgentState":
        """Return new state with updated token usage."""
        return self.model_copy(update={"token_usage": usage})

    def with_cost(self, cost: float) -> "AgentState":
        """Return new state with updated total cost."""
        return self.model_copy(update={"total_cost": cost})

    def with_context_window(self, percent: float) -> "AgentState":
        """Return new state with updated context window percentage."""
        return self.model_copy(update={"context_window_percent": percent})

    def with_todos(self, todos: List[Todo]) -> "AgentState":
        """Return new state with updated todo list."""
        return self.model_copy(update={"todos": todos})

    def with_task(self, task_id: Optional[str]) -> "AgentState":
        """Return new state with updated current task ID."""
        return self.model_copy(update={"current_task_id": task_id})


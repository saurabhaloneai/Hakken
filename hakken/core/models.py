"""
Core data models and enums for the DeepAgent system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime


class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    role: str
    content: str
    tool_calls: Optional[List[Dict]] = None


@dataclass
class EnhancedAgentState:
    messages: List[Message] = field(default_factory=list)
    files: Dict[str, str] = field(default_factory=dict)
    plan: Optional[Dict] = None
    current_step: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
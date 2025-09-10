import json
import os
import contextlib
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

from client.openai_client import APIConfiguration
from history.conversation_history import HistoryConfiguration


class ConversationState(Enum):
    WAITING_FOR_INPUT = "waiting"
    PROCESSING = "processing"
    EXECUTING_TOOLS = "executing"
    STREAMING_RESPONSE = "streaming"


@dataclass
class AgentConfig:
    MAX_TEXT_LENGTH: int = 4000
    COMMAND_PREVIEW_MAX_LENGTH: int = 180
    ARGS_PREVIEW_MAX_LENGTH: int = 140
    TOKEN_ESTIMATION_RATIO: int = 4
    INTERRUPT_TIMEOUT: float = 2.0
    STATUS_DISPLAY_DELAY: float = 0.3
    MAX_CONTEXT_BUFFER: int = 1024
    DEFAULT_TEMPERATURE: float = 0.2
    DEFAULT_MAX_TOKENS: int = 8000
    DEFAULT_CONTEXT_LIMIT: int = 120000


@dataclass
class AgentState:
    is_in_task: bool = False
    pending_user_instruction: str = ""
    tools_schema_cache: Optional[Tuple[str, int]] = None
    current_state: ConversationState = ConversationState.WAITING_FOR_INPUT


class AgentConfiguration:
    def __init__(self):
        self.api_config = APIConfiguration.from_environment()
        self.history_config = HistoryConfiguration.from_environment()


class StateManager:
    
    def __init__(self, config: Optional[AgentConfiguration] = None):
        self.config = config or AgentConfiguration()
        self.agent_config = AgentConfig()
        self.state = AgentState()
        self.logger = logging.getLogger(__name__)
    
    def get_openai_env_limits(self) -> Dict[str, int]:
        return {
            "user_requested_max_out": int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", str(self.agent_config.DEFAULT_MAX_TOKENS))),
            "context_limit": int(os.getenv("OPENAI_CONTEXT_LIMIT", str(self.agent_config.DEFAULT_CONTEXT_LIMIT))),
            "buffer_tokens": int(os.getenv("OPENAI_OUTPUT_BUFFER_TOKENS", str(self.agent_config.MAX_CONTEXT_BUFFER))),
        }
    
    def get_temperature(self) -> float:
        return float(os.getenv("OPENAI_TEMPERATURE", str(self.agent_config.DEFAULT_TEMPERATURE)))
    
    def compute_max_output_tokens(self, estimated_input_tokens: int, limits: Dict[str, int]) -> int:
        safe_output_cap = max(
            256, 
            limits["context_limit"] - estimated_input_tokens - limits["buffer_tokens"]
        )
        return max(256, min(limits["user_requested_max_out"], safe_output_cap))
    
    def estimate_tokens(self, obj: Any) -> int:
        try:
            serialized = json.dumps(obj, ensure_ascii=False)
        except Exception:
            try:
                serialized = str(obj)
            except Exception:
                serialized = ""
        return max(0, (len(serialized) + self.agent_config.TOKEN_ESTIMATION_RATIO - 1) // self.agent_config.TOKEN_ESTIMATION_RATIO)
    
    def estimate_tools_tokens(self, tools_description: list) -> int:
        try:
            import hashlib
            serialized = json.dumps(tools_description, sort_keys=True, ensure_ascii=False)
            tools_hash = hashlib.md5(serialized.encode()).hexdigest()
            
            if self.state.tools_schema_cache is not None:
                cached_hash, cached_tokens = self.state.tools_schema_cache
                if cached_hash == tools_hash:
                    return cached_tokens
            
            estimated_tokens = self.estimate_tokens(tools_description)
            self.state.tools_schema_cache = (tools_hash, estimated_tokens)
            return estimated_tokens
        except Exception:
            return self.estimate_tokens(tools_description)
    
    def estimate_total_tokens(self, messages: list, tools_description: list) -> int:
        message_tokens = self.estimate_tokens(messages)
        tools_tokens = self.estimate_tools_tokens(tools_description)
        return message_tokens + tools_tokens
    
    def get_prefs_path(self) -> Path:
        base = Path(os.getcwd()) / ".hakken"
        with contextlib.suppress(Exception):
            base.mkdir(exist_ok=True)
        return base / "agent_prefs.json"
    
    def load_prefs(self) -> Dict[str, Any]:
        path = self.get_prefs_path()
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8") or "{}")
        except Exception as e:
            self.logger.error(f"Failed to load preferences: {e}")
        return {}
    
    def save_prefs(self, data: Dict[str, Any]) -> None:
        path = self.get_prefs_path()
        try:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), 
                encoding="utf-8"
            )
        except Exception as e:
            self.logger.error(f"Failed to save preferences: {e}")
    
    def truncate_string(self, text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        return text[:max_length].rstrip() + "…"

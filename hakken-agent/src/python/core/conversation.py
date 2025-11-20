from typing import List, Optional
from datetime import datetime
from .message import Message, system_message, user_message, assistant_message, tool_message
import json
from pathlib import Path

class ConversationHistory:
    """Manages conversation history with structured Message objects"""
    
    def __init__(self, max_messages: Optional[int] = None):
        self.messages: List[Message] = []
        self.max_messages = max_messages
    
    def add_system(self, content: str, metadata: Optional[dict] = None) -> Message:
        """Add a system message to the conversation"""
        msg = system_message(content)
        if metadata:
            msg.metadata = metadata
        self.messages.append(msg)
        self._trim_if_needed()
        return msg
    
    def add_user(self, content: str, metadata: Optional[dict] = None) -> Message:
        """Add a user message to the conversation"""
        msg = user_message(content)
        if metadata:
            msg.metadata = metadata
        self.messages.append(msg)
        self._trim_if_needed()
        return msg
    
    def add_assistant(self, content: str, metadata: Optional[dict] = None) -> Message:
        """Add an assistant message to the conversation"""
        msg = assistant_message(content)
        if metadata:
            msg.metadata = metadata
        self.messages.append(msg)
        self._trim_if_needed()
        return msg
    
    def add_tool(self, content: str, metadata: Optional[dict] = None) -> Message:
        """Add a tool message to the conversation"""
        msg = tool_message(content)
        if metadata:
            msg.metadata = metadata
        self.messages.append(msg)
        self._trim_if_needed()
        return msg
    
    def _trim_if_needed(self):
        """Trim messages if max_messages is set and exceeded"""
        if self.max_messages and len(self.messages) > self.max_messages:
            # Keep system messages and trim from the middle
            system_msgs = [m for m in self.messages if m.role == "system"]
            other_msgs = [m for m in self.messages if m.role != "system"]
            
            # Keep the most recent messages
            keep_count = self.max_messages - len(system_msgs)
            other_msgs = other_msgs[-keep_count:]
            
            self.messages = system_msgs + other_msgs
    
    def get_messages_for_api(self) -> List[dict]:
        """Convert Message objects to API-compatible dictionaries"""
        return [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in self.messages
        ]
    
    def get_last_n(self, n: int) -> List[Message]:
        """Get the last n messages"""
        return self.messages[-n:] if n > 0 else []
    
    def get_by_role(self, role: str) -> List[Message]:
        """Get all messages with a specific role"""
        return [msg for msg in self.messages if msg.role == role]
    
    def clear(self):
        """Clear all messages"""
        self.messages = []
    
    def save_to_file(self, filepath: str):
        """Save conversation history to a JSON file"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "saved_at": datetime.now().isoformat(),
            "message_count": len(self.messages),
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "metadata": msg.metadata,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in self.messages
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_from_file(self, filepath: str):
        """Load conversation history from a JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.messages = [
            Message(
                role=msg_data["role"],
                content=msg_data["content"],
                metadata=msg_data.get("metadata", {}),
                timestamp=datetime.fromisoformat(msg_data["timestamp"])
            )
            for msg_data in data["messages"]
        ]
    
    def get_summary(self) -> dict:
        """Get a summary of the conversation"""
        role_counts = {}
        for msg in self.messages:
            role_counts[msg.role] = role_counts.get(msg.role, 0) + 1
        
        return {
            "total_messages": len(self.messages),
            "by_role": role_counts,
            "first_message": self.messages[0].timestamp.isoformat() if self.messages else None,
            "last_message": self.messages[-1].timestamp.isoformat() if self.messages else None
        }
    
    def __len__(self) -> int:
        return len(self.messages)
    
    def __repr__(self) -> str:
        return f"ConversationHistory(messages={len(self.messages)})"

from typing import List, Optional
from dataclasses import dataclass
from rich.console import Console
from rich.markdown import Markdown
from datetime import datetime

from .theme import UITheme
from .responsive_config import ResponsiveConfig


@dataclass
class ConversationMessage:
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime


class ConversationDisplay:
    
    def __init__(self, console: Console):
        self.console = console
        self.responsive = ResponsiveConfig(console)
        self.conversation_history: List[ConversationMessage] = []
        self.max_history_display = 10  # Show last 10 messages max
    
    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation history"""
        message = ConversationMessage(
            role='user',
            content=content,
            timestamp=datetime.now()
        )
        self.conversation_history.append(message)
        self._display_user_message(message)
    
    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation history"""
        message = ConversationMessage(
            role='assistant', 
            content=content,
            timestamp=datetime.now()
        )
        self.conversation_history.append(message)
        self._display_assistant_message(message)
    
    def _display_user_message(self, message: ConversationMessage) -> None:
        """Display a user message (clean, no boxes like Claude)"""
        # Move up to replace the input line and display properly formatted
        self.console.print(f"[bold {UITheme.ACCENT}]❯ {message.content}[/bold {UITheme.ACCENT}]")
    
    def _display_assistant_message(self, message: ConversationMessage) -> None:
        """Display assistant message (clean, no boxes like Claude)"""
        self.console.print(f"\n[{UITheme.PRIMARY}]● Assistant:[/{UITheme.PRIMARY}]\n")
        self.console.print(Markdown(message.content))
    
    def redisplay_conversation(self, messages_to_show: Optional[int] = None) -> None:
        """Redisplay the conversation history (useful for context refresh)"""
        if not self.conversation_history:
            return
            
        messages_count = messages_to_show or self.max_history_display
        recent_messages = self.conversation_history[-messages_count:]
        
        # Clear screen and redisplay
        self.console.clear()
        
        # Display header
        self.console.print(f"[bold {UITheme.PRIMARY}]Conversation History[/bold {UITheme.PRIMARY}]\n")
        
        # Display each message
        for message in recent_messages:
            if message.role == 'user':
                self._display_user_message(message)
            else:
                self._display_assistant_message(message)
    
    def clear_conversation(self) -> None:
        """Clear the conversation history"""
        self.conversation_history.clear()
    
    def get_last_user_message(self) -> Optional[ConversationMessage]:
        """Get the most recent user message"""
        for message in reversed(self.conversation_history):
            if message.role == 'user':
                return message
        return None
    
    def get_last_assistant_message(self) -> Optional[ConversationMessage]:
        """Get the most recent assistant message"""
        for message in reversed(self.conversation_history):
            if message.role == 'assistant':
                return message
        return None

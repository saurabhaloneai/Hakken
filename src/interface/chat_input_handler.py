from rich.console import Console
from .conversation_display import ConversationDisplay
from .theme import UITheme


class ChatInputHandler:
    """
    Enhanced input handler that creates a Claude-like chat interface
    where inputs become part of conversation history
    """
    
    def __init__(self, console: Console):
        self.console = console
        self.conversation = ConversationDisplay(console)
        
    async def get_chat_input(self, prompt: str = "What would you like me to help you with?") -> str:
        """
        Get user input in a chat-like interface where the input becomes part of conversation history
        """
        # Display a minimal input indicator like Claude
        if len(self.conversation.conversation_history) == 0:
            # First time - show the prompt
            self.console.print(f"\n[{UITheme.INFO}]{prompt}[/{UITheme.INFO}]")
        
        # Simple input prompt like Claude
        self.console.print(f"\n[{UITheme.MUTED}]❯[/{UITheme.MUTED}] ", end="")
        
        try:
            user_input = input("").strip()
            
            if user_input:
                # Move cursor up to overwrite the plain input line with styled version
                # This prevents the double display issue
                print("\033[F\033[K", end="")  # Move up one line and clear it
                
                # Add to conversation history (this will display it properly styled)
                self.conversation.add_user_message(user_input)
                
                # Show processing indicator
                self.console.print(f"\n[{UITheme.MUTED}]◯ Processing your request...[/{UITheme.MUTED}]")
            
            return user_input
            
        except (KeyboardInterrupt, EOFError):
            raise KeyboardInterrupt()
    
    def display_assistant_response(self, content: str) -> None:
        """Display assistant response as part of conversation history"""
        if content and content.strip():
            self.conversation.add_assistant_message(content)
    
    def get_conversation_display(self) -> ConversationDisplay:
        """Get access to the conversation display for advanced operations"""
        return self.conversation
    
    def clear_conversation(self) -> None:
        """Clear the conversation history"""
        self.conversation.clear_conversation()
    
    def redisplay_conversation(self) -> None:
        """Redisplay the entire conversation"""
        self.conversation.redisplay_conversation()

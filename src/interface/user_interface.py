from typing import Optional, List, Dict, Any
from rich.console import Console
from interface.base_ui import BaseUI, Message
from interface.display_ui import DisplayUI
from interface.interaction_ui import InteractionUI


class HakkenCodeUI(DisplayUI, InteractionUI):
    """Main UI class that combines display and interaction functionality"""
    
    def __init__(self, console: Optional[Console] = None):
        # Initialize the base classes
        BaseUI.__init__(self, console)
    
    # ========================================
    # Agent Compatibility Methods
    # ========================================
    
    def print_error(self, message: str):
        """Compatibility method for agent error printing"""
        self.display_error(message)
    
    def print_info(self, message: str):
        """Compatibility method for agent info printing"""
        self.display_info(message)
    
    def print_simple_message(self, message: str, prefix: str = ""):
        """Compatibility method for simple message printing"""
        if message and message.strip():
            self._ensure_spacing_before_output()
            if prefix:
                from rich.text import Text
                text = Text()
                text.append(f"{prefix} ", style=f"bold {self.colors['blue']}")
                text.append(message, style=self.colors['light_gray'])
                self.console.print(text)
            else:
                self.console.print(message, style=self.colors['light_gray'])
            self._mark_output_with_newline(message)
    
    def print_assistant_message(self, message: str):
        """Compatibility method for assistant message printing"""
        self.display_assistant_message(message)
    
    def start_stream_display(self):
        """Compatibility method for starting stream display"""
        self.start_assistant_response()
    
    def stop_stream_display(self):
        """Compatibility method for stopping stream display"""
        self.finish_assistant_response()
    
    def print_streaming_content(self, content: str):
        """Compatibility method for streaming content"""
        self.stream_content(content)

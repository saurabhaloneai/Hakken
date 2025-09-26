from typing import Optional, List, Dict, Any
from rich.console import Console
from interface.base_ui import BaseUI, Message
from interface.display_ui import DisplayUI
from interface.interaction_ui import InteractionUI


class HakkenCodeUI(DisplayUI, InteractionUI):
     
    
    def __init__(self, console: Optional[Console] = None):
         
        BaseUI.__init__(self, console)
 
    def print_error(self, message: str):
         
        self.display_error(message)
    
    def print_info(self, message: str):
         
        self.display_info(message)
    
    def print_simple_message(self, message: str, prefix: str = ""):
         
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
        self.display_assistant_message(message)
    
    def start_stream_display(self):
        self.start_assistant_response()
    
    def stop_stream_display(self):
        self.finish_assistant_response()
    
    def print_streaming_content(self, content: str):
        self.stream_content(content)

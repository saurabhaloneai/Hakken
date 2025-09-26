import os
import sys
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.status import Status
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Message:
    role: str 
    content: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BaseUI:
    def __init__(self, console: Optional[Console] = None):
        if console is None:
            console = Console(force_terminal=True, color_system="truecolor", width=80)
        self.console = console
        self.conversation: List[Message] = []
        self.todos: List[Dict[str, Any]] = []
        self._streaming_content = ""
        self._is_streaming = False
        self._spinner_active = False
        self._status: Optional[Status] = None
        self._last_output_had_newline = True  
        
        self.colors = {
            'orange': '#ff6b35',        
            'blue': '#00d4ff',          
            'gray': '#8b949e',          
            'light_gray': '#c9d1d9',    
            'white': '#f0f6fc',         
            'green': '#00ff88',         
            'red': '#ff4757',           
            'yellow': '#ffd700',        
            'purple': '#b794f6',        
            'pink': '#ff79c6',          
            'dark_bg': '#0d1117',       
            'border': '#30363d',        
            'input_bg': '#161b22',      
        }

    def _ensure_spacing_before_output(self):
        if not self._last_output_had_newline:
            print()
            self._last_output_had_newline = True
    
    def _mark_output_with_newline(self, content: str = ""):
        self._last_output_had_newline = content.endswith('\n') if content else True
    # TODO : fix this  
    def start_spinner(self, text: str = "Thinking", spinner_style: str = "dots"):
        self.stop_spinner()
        
        if not self._last_output_had_newline:
            print()
        
        try:
            spinner_options = [spinner_style, 'dots', 'line', 'simpleDots', 'arc']
            
            for spinner in spinner_options:
                try:
                    self._status = Status(
                        text,
                        console=self.console,
                        spinner=spinner,
                        spinner_style=self.colors['blue'],
                        speed=1.0
                    )
                    
                    self._status.start()
                    self._spinner_active = True
                    self._last_output_had_newline = False
                    break  
                    
                except Exception:
                    continue  
                    
            if not self._spinner_active:
                raise Exception("All spinner types failed")
            
        except Exception as e:
            self._status = None
            self._spinner_active = True
            spinner_icon = "⚙️" if "thinking" in text.lower() else "🔄"
            self.console.print(f"[{self.colors['blue']}]{spinner_icon} {text}...[/]", end="")
            self._last_output_had_newline = False
    
    def stop_spinner(self):
        if self._status is not None:
            try:
                self._status.stop()
            except Exception:
                pass
            finally:
                self._status = None
                self._spinner_active = False
                self._last_output_had_newline = True
        elif self._spinner_active:
            print("\r" + " " * 60 + "\r", end="", flush=True)
            self._spinner_active = False
            self._last_output_had_newline = True
    
    def update_spinner_text(self, text: str):
        """Update spinner/status text while it's running"""
        if self._status is not None and self._spinner_active:
            try:
                self._status.update(text)
            except Exception:
                self.stop_spinner()
                self.start_spinner(text)
        elif self._spinner_active:
            self.stop_spinner()
            self.start_spinner(text)
    
    def update_todos(self, todos: List[Dict[str, Any]]):
        self.todos = todos

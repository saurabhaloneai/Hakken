import os
import sys
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.status import Status
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Message:
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BaseUI:
    """Base UI class with common functionality for colors, console, and spacing management"""
    
    def __init__(self, console: Optional[Console] = None):
        # Force color and feature support for Rich console
        if console is None:
            console = Console(force_terminal=True, color_system="truecolor", width=80)
        self.console = console
        self.conversation: List[Message] = []
        self.todos: List[Dict[str, Any]] = []
        self._streaming_content = ""
        self._is_streaming = False
        self._spinner_active = False
        self._status: Optional[Status] = None
        # FIXED: Better spacing control
        self._last_output_had_newline = True  # Track if last output ended with newline
        
        # Modern cyberpunk-inspired color scheme
        self.colors = {
            'orange': '#ff6b35',        # Vibrant coral-orange for star and accents
            'blue': '#00d4ff',          # Electric cyan-blue for highlights  
            'gray': '#8b949e',          # Soft muted gray for secondary text
            'light_gray': '#c9d1d9',    # Light gray for subtle text
            'white': '#f0f6fc',         # Clean bright white for main text
            'green': '#00ff88',         # Electric green for success
            'red': '#ff4757',           # Bright red for errors  
            'yellow': '#ffd700',        # Golden yellow for warnings
            'purple': '#b794f6',        # Soft purple for special elements
            'pink': '#ff79c6',          # Accent pink for highlights
            'dark_bg': '#0d1117',       # Deep dark background
            'border': '#30363d',        # Subtle border color
            'input_bg': '#161b22',      # Dark input background
        }

    def _ensure_spacing_before_output(self):
        """Add spacing before output only when needed"""
        if not self._last_output_had_newline:
            print()
            self._last_output_had_newline = True
    
    def _mark_output_with_newline(self, content: str = ""):
        """Mark that output was produced, track if it ends with newline"""
        self._last_output_had_newline = content.endswith('\n') if content else True
    
    def start_spinner(self, text: str = "Thinking", spinner_style: str = "dots"):
        """Start animated Rich Status spinner with custom text and style."""
        # Stop any existing status/spinner
        self.stop_spinner()
        
        # Ensure we have a newline before starting spinner
        if not self._last_output_had_newline:
            print()
        
        try:
            # Create Rich Status spinner with proper configuration
            # Try different spinners for better compatibility
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
                    
                    # Start the spinner
                    self._status.start()
                    self._spinner_active = True
                    self._last_output_had_newline = False
                    break  # Success, exit the loop
                    
                except Exception:
                    continue  # Try next spinner
                    
            if not self._spinner_active:
                raise Exception("All spinner types failed")
            
        except Exception as e:
            # Fallback to simple text display if Rich Status fails
            self._status = None
            self._spinner_active = True
            spinner_icon = "⚙️" if "thinking" in text.lower() else "🔄"
            self.console.print(f"[{self.colors['blue']}]{spinner_icon} {text}...[/]", end="")
            self._last_output_had_newline = False
    
    def stop_spinner(self):
        """Stop the animated spinner/status"""
        if self._status is not None:
            # Stop Rich Status spinner
            try:
                self._status.stop()
            except Exception:
                pass
            finally:
                self._status = None
                self._spinner_active = False
                self._last_output_had_newline = True
        elif self._spinner_active:
            # Stop fallback text spinner
            print("\r" + " " * 60 + "\r", end="", flush=True)
            self._spinner_active = False
            self._last_output_had_newline = True
    
    def update_spinner_text(self, text: str):
        """Update spinner/status text while it's running"""
        if self._status is not None and self._spinner_active:
            try:
                self._status.update(text)
            except Exception:
                # If update fails, fall back to stopping and restarting
                self.stop_spinner()
                self.start_spinner(text)
        elif self._spinner_active:
            # For fallback spinner, restart with new text
            self.stop_spinner()
            self.start_spinner(text)
    
    def update_todos(self, todos: List[Dict[str, Any]]):
        """Update the todos list"""
        self.todos = todos

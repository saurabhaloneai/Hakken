import os
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box
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


class HakkenCodeUI:
    """UI that matches Hakken Code interface exactly"""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.conversation: List[Message] = []
        self.todos: List[Dict[str, Any]] = []
        self._streaming_content = ""
        self._is_streaming = False
        self._spinner_active = False
        self._status: Optional[Status] = None
        
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
        
        # Spinner/status initialized lazily in start_spinner
    
    def display_welcome_header(self):
        """Display the exact welcome header from Hakken Code"""
        # Get current working directory
        current_dir = os.getcwd()
        home_dir = os.path.expanduser("~")
        
        # Create the bordered welcome panel exactly like the screenshot
        welcome_content = Text()
        welcome_content.append("✱ Welcome to Hakken Code!\n\n", style=f"bold {self.colors['orange']}")
        welcome_content.append("/help for help, /status for your current setup\n\n", style=self.colors['gray'])
        welcome_content.append(f"cwd: {current_dir}", style=self.colors['gray'])
        
        panel = Panel(
            welcome_content,
            border_style=self.colors['orange'],
            box=box.ROUNDED,
            padding=(1, 1),
            width=60
        )
        
        self.console.print(panel)
        self.console.print()
        
        # Tips section exactly like screenshot  
        self.console.print(f"[{self.colors['gray']}]Tips for getting started:[/]\n")
        self.console.print(f"[{self.colors['gray']}]  Run /init to create a Hakken.md file with instructions for Hakken[/]")
        self.console.print(f"[{self.colors['gray']}]  Use Hakken to help with file analysis, editing, bash commands and git[/]")
        self.console.print(f"[{self.colors['gray']}]  Be as specific as you would with another engineer for the best results[/]\n")
        
        # Only show note if actually in home directory
        if current_dir == home_dir:
            self.console.print(f"[{self.colors['yellow']}]Note: You have launched Hakken in your home directory. For the best experience, launch it in a project directory instead.[/]\n")
    
    def display_credit_warning(self, message: str = ""):
        """Display credit warning exactly like Hakken Code"""
        warning_text = Text()
        warning_text.append("└ ", style=self.colors['red'])
        warning_text.append("Credit balance too low · Add funds: https://console.anthropic.com/settings/billing", 
                          style=self.colors['red'])
        self.console.print(warning_text)
        self.console.print()
    
    async def get_user_input(self, prompt: str = "") -> str:
        """Get user input with exact Hakken Code styling"""
        # Show the exact prompt style: "> " with cursor
        try:
            # Display the prompt exactly like Hakken Code
            prompt_text = Text()
            prompt_text.append("> ", style=f"bold {self.colors['white']}")
            self.console.print(prompt_text, end="")
            
            user_input = input("").strip()
            if user_input:
                # Add to conversation history
                self.conversation.append(Message('user', user_input))
            return user_input
        except (KeyboardInterrupt, EOFError):
            raise KeyboardInterrupt()
    
    def display_shortcuts_help(self):
        """Display shortcuts help like Hakken Code"""
        self.console.print(f"[{self.colors['gray']}]? for shortcuts[/]")
    
    def start_assistant_response(self):
        """Start streaming response - no extra formatting, just content"""
        self._is_streaming = True
        self._streaming_content = ""
        # Don't print anything here - let the content stream directly
    
    def stream_content(self, chunk: str):
        """Stream content exactly like Hakken - just print the content"""
        if self._is_streaming:
            self._streaming_content += chunk
            print(chunk, end="", flush=True)
    
    def finish_assistant_response(self):
        """Finish streaming and save to conversation"""
        if self._is_streaming and self._streaming_content:
            self.conversation.append(Message('assistant', self._streaming_content))
            print()  # New line after streaming
            self._streaming_content = ""
        self._is_streaming = False
    
    def display_assistant_message(self, content: str):
        """Display complete assistant message (non-streaming)"""
        if content and content.strip():
            print(content)
            print()
            self.conversation.append(Message('assistant', content))
    
    def display_error(self, message: str):
        """Display error message with Hakken Code styling"""
        error_text = Text()
        error_text.append("Error: ", style=f"bold {self.colors['red']}")
        error_text.append(message, style=self.colors['red'])
        self.console.print(error_text)
    
    def display_success(self, message: str):
        """Display success message"""
        success_text = Text()
        success_text.append("✓ ", style=self.colors['green'])
        success_text.append(message, style=self.colors['green'])
        self.console.print(success_text)
    
    def display_warning(self, message: str):
        """Display warning message"""
        warning_text = Text()
        warning_text.append("⚠ ", style=self.colors['yellow'])
        warning_text.append(message, style=self.colors['yellow'])
        self.console.print(warning_text)
    
    def display_info(self, message: str):
        """Display info message"""
        self.console.print(f"[{self.colors['gray']}]{message}[/]")
    
    def start_spinner(self, text: str = "Thinking", spinner_style: str = "dots"):
        """Start animated spinner with custom text and style (uses Rich Status)."""
        # Stop any existing status/spinner
        if self._status is not None:
            try:
                self._status.stop()
            except Exception:
                pass
            self._status = None

        # Create and start a new Status with the requested spinner style
        self._status = Status(text, console=self.console, spinner=spinner_style, spinner_style=self.colors['blue'])
        self._status.start()
        self._spinner_active = True
    
    def stop_spinner(self):
        """Stop the animated spinner/status"""
        if self._status is not None:
            try:
                self._status.stop()
            except Exception:
                pass
            self._status = None
        self._spinner_active = False
    
    def update_spinner_text(self, text: str):
        """Update spinner/status text while it's running"""
        if self._status is not None:
            try:
                self._status.update(text)
            except Exception:
                pass
    
    @staticmethod
    def get_available_spinner_styles():
        """Get list of available Rich spinner styles"""
        # Run `python -m rich.spinner` to see all available styles
        return [
            "dots", "dots2", "dots3", "dots4", "dots5", "dots6", "dots7", "dots8", 
            "dots9", "dots10", "dots11", "dots12", "line", "line2", "pipe", "simpleDots",
            "simpleDotsScrolling", "star", "star2", "flip", "hamburger", "growVertical", 
            "growHorizontal", "balloon", "balloon2", "noise", "bounce", "boxBounce", 
            "boxBounce2", "triangle", "arc", "circle", "squareCorners", "circleQuarters", 
            "circleHalves", "squish", "toggle", "toggle2", "toggle3", "toggle4", "toggle5", 
            "toggle6", "toggle7", "toggle8", "toggle9", "toggle10", "toggle11", "toggle12", 
            "toggle13", "arrow", "arrow2", "arrow3", "bouncingBar", "bouncingBall"
        ]
    
    async def confirm_action(self, message: str) -> bool:
        """Simple confirmation like Hakken Code"""
        self.console.print(f"\n{message}")
        
        prompt_text = Text()
        prompt_text.append("Continue? (y/n): ", style=self.colors['gray'])
        self.console.print(prompt_text, end="")
        
        response = input("").strip().lower()
        return response.startswith('y')
    
    def display_todos(self, todos: Optional[List[Dict[str, Any]]] = None):
        """Display todos in elegant, clean format with visual hierarchy"""
        todos_to_show = todos or self.todos
        
        if not todos_to_show:
            return
        
        # Create elegant header with modern styling
        header_text = Text()
        header_text.append("✦ ", style=f"bold {self.colors['pink']}")
        header_text.append("Project Tasks", style=f"bold {self.colors['blue']}")
        
        # Create a subtle border panel for the todos
        todo_content = Text()
        
        for i, todo in enumerate(todos_to_show, 1):
            status = todo.get('status', 'pending')
            task = todo.get('task', todo.get('content', 'No description'))
            priority = todo.get('priority', 'normal')
            
            # Modern vibrant status indicators
            if status == 'completed':
                icon = "✓"
                icon_color = self.colors['green']
                task_style = f"dim {self.colors['gray']}"
            elif status == 'in_progress':
                icon = "◉"
                icon_color = self.colors['purple']
                task_style = self.colors['white']
            else:
                icon = "○"
                icon_color = self.colors['gray']
                task_style = self.colors['light_gray']
            
            # Add task with clean formatting
            todo_content.append(f"  ", style="")
            todo_content.append(icon, style=f"bold {icon_color}")
            todo_content.append("  ", style="")
            todo_content.append(task, style=task_style)
            
            if i < len(todos_to_show):
                todo_content.append("\n", style="")
        
        # Create a clean panel with minimal borders
        panel = Panel(
            todo_content,
            title=header_text,
            title_align="left",
            border_style=self.colors['border'],
            box=box.ROUNDED,
            padding=(0, 1),
            width=80
        )
        
        self.console.print()
        self.console.print(panel)
        self.console.print()
    
    def update_todos(self, todos: List[Dict[str, Any]]):
        """Update the todos list"""
        self.todos = todos
    
    
    def display_tool_execution(self, tool_name: str, args: dict, status: str = "running"):
        """Display tool execution status"""
        if status == "running":
            self.display_info(f"Running {tool_name}...")
        elif status == "success":
            self.display_success(f"{tool_name} completed")
        elif status == "error":
            self.display_error(f"{tool_name} failed")
    
    async def get_choice(self, prompt: str, choices: List[str]) -> str:
        """Get user choice with Hakken Code styling"""
        self.console.print(f"\n{prompt}")
        for i, choice in enumerate(choices, 1):
            choice_text = Text()
            choice_text.append(f"  {i}. ", style=self.colors['gray'])
            choice_text.append(choice, style=self.colors['white'])
            self.console.print(choice_text)
        
        while True:
            prompt_text = Text()
            prompt_text.append(f"\nChoice (1-{len(choices)}): ", style=self.colors['gray'])
            self.console.print(prompt_text, end="")
            
            try:
                response = input("").strip()
                if response.isdigit():
                    choice_num = int(response)
                    if 1 <= choice_num <= len(choices):
                        return choices[choice_num - 1]
                
                self.display_error("Invalid choice. Please try again.")
            except (ValueError, KeyboardInterrupt):
                self.display_error("Invalid input.")
    
    
    def display_status(self, context_usage: str = "", cost: str = ""):
        """Display system status"""
        status_parts = []
        if context_usage:
            status_parts.append(f"Context: {context_usage}")
        if cost:
            status_parts.append(f"Cost: ${cost}")
        
        if status_parts:
            status_text = " | ".join(status_parts)
            self.display_info(status_text)

    def show_user_message_with_credit_warning(self, user_message: str):
        """Show user message followed by credit warning like in the image"""
        # Display user input
        user_text = Text()
        user_text.append("> ", style=f"bold {self.colors['white']}")
        user_text.append(user_message, style=self.colors['white'])
        self.console.print(user_text)
        
        # Display credit warning immediately after
        self.display_credit_warning()


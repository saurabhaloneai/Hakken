import os
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box
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
        
        # Exact colors from Hakken Code interface (dark theme)
        self.colors = {
            'orange': '#ff8c42',        # Orange star and borders
            'blue': '#4a9eff',          # Blue accents  
            'gray': '#6b7280',          # Muted gray text
            'light_gray': '#9ca3af',    # Lighter gray
            'white': '#f9fafb',         # Main white text
            'green': '#10b981',         # Success green
            'red': '#ef4444',           # Error red  
            'yellow': '#f59e0b',        # Warning yellow
            'dark_bg': '#111827',       # Dark background
            'border': '#374151',        # Border color
            'input_bg': '#1f2937',      # Input background
        }
    
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
    
    async def confirm_action(self, message: str) -> bool:
        """Simple confirmation like Hakken Code"""
        self.console.print(f"\n{message}")
        
        prompt_text = Text()
        prompt_text.append("Continue? (y/n): ", style=self.colors['gray'])
        self.console.print(prompt_text, end="")
        
        response = input("").strip().lower()
        return response.startswith('y')
    
    def display_todos(self, todos: Optional[List[Dict[str, Any]]] = None):
        """Display todos in clean format"""
        todos_to_show = todos or self.todos
        
        if not todos_to_show:
            self.display_info("No todos found.")
            return
        
        self.console.print("\nTodos:")
        for i, todo in enumerate(todos_to_show, 1):
            status = todo.get('status', 'pending')
            task = todo.get('task', todo.get('content', 'No description'))
            priority = todo.get('priority', 'normal')
            
            # Simple status indicators with Hakken Code colors
            if status == 'completed':
                icon = f"[{self.colors['green']}]✓[/]"
            elif status == 'in_progress':
                icon = f"[{self.colors['yellow']}]●[/]"
            else:
                icon = f"[{self.colors['gray']}]○[/]"
            
            # Priority color
            if priority == 'high':
                task_color = self.colors['red']
            elif priority == 'medium':
                task_color = self.colors['yellow']
            else:
                task_color = self.colors['white']
            
            self.console.print(f"  {icon} [{task_color}]{task}[/]")
        
        self.console.print()
    
    def update_todos(self, todos: List[Dict[str, Any]]):
        """Update the todos list"""
        self.todos = todos
    
    def add_todo(self, task: str, priority: str = "normal", status: str = "pending"):
        """Add a new todo"""
        todo = {
            'id': len(self.todos) + 1,
            'task': task,
            'priority': priority,
            'status': status
        }
        self.todos.append(todo)
        return todo
    
    def update_todo_status(self, todo_id: int, status: str) -> bool:
        """Update todo status"""
        for todo in self.todos:
            if todo.get('id') == todo_id:
                todo['status'] = status
                return True
        return False
    
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
    
    def clear_screen(self):
        """Clear the console"""
        self.console.clear()
    
    def get_conversation_context(self, max_messages: int = 20) -> List[Dict[str, str]]:
        """Get conversation history for AI context"""
        recent_messages = self.conversation[-max_messages:]
        return [
            {"role": msg.role, "content": msg.content}
            for msg in recent_messages
        ]
    
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


class SimpleUI:
    """Clean, minimal UI inspired by Hakken Code interface with dark theme"""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.conversation: List[Message] = []
        self.todos: List[Dict[str, Any]] = []
        self._streaming_content = ""
        self._is_streaming = False
        
        # Dark theme colors matching Hakken Code
        self.colors = {
            'user': '#4a9eff',          # Blue for user input
            'assistant': '#f9fafb',     # White for assistant
            'muted': '#6b7280',         # Gray for secondary text
            'warning': '#f59e0b',       # Orange for warnings
            'error': '#ef4444',         # Red for errors
            'success': '#10b981',       # Green for success
            'accent': '#ff8c42',        # Orange accent like Hakken Code
        }
    
    def clear_screen(self):
        """Clear the console"""
        self.console.clear()
    
    def print_welcome(self):
        """Display welcome message like Hakken Code with dark theme"""
        welcome_text = Text()
        welcome_text.append("✱ Welcome to Your Assistant!\n\n", style=f"bold {self.colors['accent']}")
        welcome_text.append("/help for help, /status for your current setup\n\n", style=self.colors['muted'])
        welcome_text.append("Ready to help with your tasks!", style=self.colors['assistant'])
        
        # Dark themed bordered box like Hakken
        panel = Panel(
            welcome_text,
            border_style=self.colors['accent'],
            box=box.ROUNDED,
            padding=(1, 2)
        )
        self.console.print(panel)
        self.console.print()
    
    async def get_user_input(self, prompt: str = "") -> str:
        """Get user input with Hakken-like styling"""
        # Show prompt like Hakken: "> " 
        prompt_text = Text()
        prompt_text.append("> ", style=f"bold {self.colors['user']}")
        self.console.print(prompt_text, end="")
        
        try:
            user_input = input("").strip()
            if user_input:
                # Add to conversation history
                self.conversation.append(Message('user', user_input))
                # Don't redisplay - input is already visible
            return user_input
        except (KeyboardInterrupt, EOFError):
            raise KeyboardInterrupt()
    
    def start_assistant_response(self):
        """Start assistant response display"""
        self._is_streaming = True
        self._streaming_content = ""
        self.console.print()  # New line before assistant response
    
    def stream_content(self, chunk: str):
        """Stream content chunk by chunk"""
        if self._is_streaming:
            self._streaming_content += chunk
            print(chunk, end="", flush=True)
    
    def finish_assistant_response(self):
        """Finish assistant response and add to conversation"""
        if self._is_streaming and self._streaming_content:
            self.conversation.append(Message('assistant', self._streaming_content))
            self.console.print()  # New line after response
            self._streaming_content = ""
        self._is_streaming = False
    
    def display_assistant_message(self, content: str):
        """Display complete assistant message (non-streaming)"""
        if content and content.strip():
            self.console.print()
            self.console.print(content, style=self.colors['assistant'])
            self.console.print()
            self.conversation.append(Message('assistant', content))
    
    def display_error(self, message: str):
        """Display error message"""
        error_text = Text()
        error_text.append("Error: ", style=f"bold {self.colors['error']}")
        error_text.append(message, style=self.colors['error'])
        self.console.print(error_text)
    
    def display_success(self, message: str):
        """Display success message"""
        success_text = Text()
        success_text.append("✓ ", style=self.colors['success'])
        success_text.append(message, style=self.colors['success'])
        self.console.print(success_text)
    
    def display_warning(self, message: str):
        """Display warning message"""
        warning_text = Text()
        warning_text.append("⚠ ", style=self.colors['warning'])
        warning_text.append(message, style=self.colors['warning'])
        self.console.print(warning_text)
    
    def display_info(self, message: str):
        """Display info message"""
        self.console.print(f"[{self.colors['muted']}]{message}[/]")
    
    async def confirm_action(self, message: str) -> bool:
        """Simple yes/no confirmation"""
        warning_text = Text()
        warning_text.append(f"\n{message}", style=self.colors['warning'])
        self.console.print(warning_text)
        
        prompt_text = Text()
        prompt_text.append("Continue? (y/n): ", style=self.colors['muted'])
        self.console.print(prompt_text, end="")
        
        response = input("").strip().lower()
        return response.startswith('y')
    
    def display_todos(self, todos: Optional[List[Dict[str, Any]]] = None):
        """Display todos in a clean format matching Hakken Code theme"""
        todos_to_show = todos or self.todos
        
        if not todos_to_show:
            self.console.print(f"[{self.colors['muted']}]No todos found.[/]")
            return
        
        # Use simple list format like Hakken Code
        self.console.print("\nTodos:")
        
        status_icons = {
            "completed": f"[{self.colors['success']}]✓[/]",
            "in_progress": f"[{self.colors['warning']}]●[/]", 
            "pending": f"[{self.colors['muted']}]○[/]"
        }
        
        priority_colors = {
            "high": self.colors['error'],
            "medium": self.colors['warning'],
            "normal": self.colors['assistant'],
            "low": self.colors['muted']
        }
        
        for todo in todos_to_show:
            status = todo.get('status', 'pending')
            task = todo.get('task', todo.get('content', 'No description'))
            priority = todo.get('priority', 'normal')
            
            status_icon = status_icons.get(status, "○")
            priority_color = priority_colors.get(priority, self.colors['assistant'])
            
            todo_text = Text()
            todo_text.append("  ", style="")
            todo_text.append(status_icon)
            todo_text.append(" ", style="")
            todo_text.append(task, style=priority_color)
            
            self.console.print(todo_text)
        
        self.console.print()
    
    # ... rest of the methods remain the same but with updated color scheme


# Maintain compatibility with existing code
class UserInterface:
    """Wrapper to maintain compatibility with existing code"""
    
    def __init__(self, console: Optional[Console] = None):
        self.ui = HakkenCodeUI(console)  # Use HakkenCodeUI for exact match
        self.console = self.ui.console
        self._interrupt_callbacks = []
    
    async def get_chat_input(self, prompt: str = "") -> str:
        return await self.ui.get_user_input(prompt)
    
    def display_assistant_response_in_chat(self, content: str):
        self.ui.display_assistant_message(content)
    
    def start_stream_display(self):
        self.ui.start_assistant_response()
    
    def print_streaming_content(self, chunk: str):
        self.ui.stream_content(chunk)
    
    def stop_stream_display(self):
        self.ui.finish_assistant_response()
    
    def print_error(self, message: str):
        self.ui.display_error(message)
    
    def print_success(self, message: str):
        self.ui.display_success(message)
    
    def print_info(self, message: str):
        self.ui.display_info(message)
    
    def print_warning(self, message: str):
        self.ui.display_warning(message)
    
    def print_assistant_message(self, content: str, emoji: str = "", use_chat: bool = False):
        self.ui.display_assistant_message(content)
    
    def display_todos(self, todos: List[Dict[str, Any]]):
        self.ui.display_todos(todos)
    
    async def confirm_action(self, message: str) -> tuple[bool, str]:
        result = await self.ui.confirm_action(message)
        return result, ""
    
    def display_welcome_header(self):
        self.ui.display_welcome_header()
    
    def display_context_info(self, context_usage: str, cost: str):
        self.ui.display_status(context_usage, cost)
    
    def add_interrupt_callback(self, callback):
        self._interrupt_callbacks.append(callback)
    
    def start_interrupt_mode(self):
        pass  # Simplified for new UI
    
    def stop_interrupt_mode(self):
        pass  # Simplified for new UI
    
    async def check_for_interrupts(self):
        pass  # Simplified for new UI
    
    async def wait_for_user_approval(self, content: str, emoji: str = "") -> tuple[bool, str]:
        result = await self.ui.confirm_action(f"Approve: {content}")
        return result, ""
    
    async def select_from_options(self, prompt: str, options: dict, emoji: str = "") -> tuple[str, dict, str]:
        choices = list(options.keys())
        selected = await self.ui.get_choice(prompt, choices)
        return selected, options[selected], ""


# Compatibility wrapper for existing code  
class UIManager:
    """Wrapper to maintain compatibility with existing code"""
    
    def __init__(self):
        self.ui = HakkenCodeUI()
        self.console = self.ui.console
    
    async def get_chat_input(self, prompt: str = "") -> str:
        return await self.ui.get_user_input(prompt)
    
    def display_assistant_response_in_chat(self, content: str):
        self.ui.display_assistant_message(content)
    
    def start_stream_display(self):
        self.ui.start_assistant_response()
    
    def print_streaming_content(self, chunk: str):
        self.ui.stream_content(chunk)
    
    def stop_stream_display(self):
        self.ui.finish_assistant_response()
    
    def print_error(self, message: str):
        self.ui.display_error(message)
    
    def print_success(self, message: str):
        self.ui.display_success(message)
    
    def print_info(self, message: str):
        self.ui.display_info(message)
    
    def display_todos(self, todos: List[Dict[str, Any]]):
        self.ui.display_todos(todos)
    
    async def confirm_action(self, message: str) -> tuple[bool, str]:
        result = await self.ui.confirm_action(message)
        return result, ""
    
    def display_welcome_header(self):
        self.ui.display_welcome_header()
    
    def display_context_info(self, context_usage: str, cost: str):
        self.ui.display_status(context_usage, cost)
    
    def display_credit_warning(self, message: str = ""):
        self.ui.display_credit_warning(message)
    
    def display_shortcuts_help(self):
        self.ui.display_shortcuts_help()
    
    def show_user_message_with_credit_warning(self, user_message: str):
        """Helper method to replicate the exact interaction from the images"""
        self.ui.show_user_message_with_credit_warning(user_message)
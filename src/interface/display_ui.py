import os
from typing import List, Dict, Any, Optional
from rich.panel import Panel
from rich.text import Text
from rich import box
from interface.base_ui import BaseUI, Message


class DisplayUI(BaseUI):
    """Display UI class for messages, panels, and visual elements"""
    
    def display_welcome_header(self):
        """Display the exact welcome header from Hakken Code"""
        # Get current working directory
        current_dir = os.getcwd()
        
        # Create the bordered welcome panel exactly like the screenshot
        welcome_content = Text()
        welcome_content.append("✱ Welcome to Hakken Code!\n", style=f"bold {self.colors['orange']}")
        welcome_content.append("/help for help, /status for your current setup\n", style=self.colors['gray'])
        welcome_content.append(f"cwd: {current_dir}", style=self.colors['gray'])
        
        # Get terminal width and make panel responsive
        terminal_width = self.console.size.width
        panel_width = min(60, terminal_width - 4)  # Leave some margin
        
        panel = Panel(
            welcome_content,
            border_style=self.colors['orange'],
            box=box.ROUNDED,
            padding=(1, 1),
            width=panel_width
        )
        
        self.console.print(panel)
        print()  # Single blank line after panel
        
        self.console.print(f"[{self.colors['gray']}]Tips for getting started:[/]")
        self.console.print(f"[{self.colors['gray']}]  Run /init to create a Hakken.md file with instructions for Hakken[/]")
        self.console.print(f"[{self.colors['gray']}]  Use Hakken to help with file analysis, editing, bash commands and git[/]")
        self.console.print(f"[{self.colors['gray']}]  Be as specific as you would with another engineer for the best results[/]")
        
        # Only show note if actually in home directory
        home_dir = os.path.expanduser("~")
        if current_dir == home_dir:
            print()  # Blank line before warning
            self.console.print(f"[{self.colors['yellow']}]Note: You have launched Hakken in your home directory. For the best experience, launch it in a project directory instead.[/]")
        
        self._last_output_had_newline = True
    
    def display_error(self, message: str):
        """Display error message with Hakken Code styling"""
        self._ensure_spacing_before_output()
        error_text = Text()
        error_text.append("Error: ", style=f"bold {self.colors['red']}")
        error_text.append(message, style=self.colors['red'])
        self.console.print(error_text)
        self._last_output_had_newline = True
    
    def display_success(self, message: str):
        """Display success message"""
        self._ensure_spacing_before_output()
        success_text = Text()
        success_text.append("✓ ", style=self.colors['green'])
        success_text.append(message, style=self.colors['green'])
        self.console.print(success_text)
        self._last_output_had_newline = True
    
    def display_warning(self, message: str):
        """Display warning message"""
        self._ensure_spacing_before_output()
        warning_text = Text()
        warning_text.append("⚠ ", style=self.colors['yellow'])
        warning_text.append(message, style=self.colors['yellow'])
        self.console.print(warning_text)
        self._last_output_had_newline = True
    
    def display_info(self, message: str):
        """Display info message"""
        self._ensure_spacing_before_output()
        self.console.print(f"[{self.colors['gray']}]{message}[/]")
        self._last_output_had_newline = True
    
    def display_assistant_message(self, content: str):
        """Display complete assistant message (non-streaming)"""
        if content and content.strip():
            self._ensure_spacing_before_output()
            self.console.print(content, style=self.colors['light_gray'])
            # FIXED: Ensure newline after assistant message
            if not content.endswith('\n'):
                print()
                self._last_output_had_newline = True
            else:
                self._mark_output_with_newline(content)
            self.conversation.append(Message('assistant', content))
    
    def display_todos(self, todos: Optional[List[Dict[str, Any]]] = None):
        """Display todos with consistent spacing"""
        todos_to_show = todos or self.todos
        
        if not todos_to_show:
            return
        
        self._ensure_spacing_before_output()
        
        header_text = Text()
        header_text.append("✦ ", style=f"bold {self.colors['pink']}")
        header_text.append("Project Tasks", style=f"bold {self.colors['blue']}")
        
        todo_content = Text()
        
        for i, todo in enumerate(todos_to_show, 1):
            status = todo.get('status', 'pending')
            task = todo.get('task', todo.get('content', 'No description'))
            
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
            
            todo_content.append("  ", style="")
            todo_content.append(icon, style=f"bold {icon_color}")
            todo_content.append("  ", style="")
            todo_content.append(task, style=task_style)
            
            if i < len(todos_to_show):
                todo_content.append("\n", style="")
        
        # Make panel responsive to terminal width
        terminal_width = self.console.size.width
        panel_width = min(80, terminal_width - 4)
        
        panel = Panel(
            todo_content,
            title=header_text,
            title_align="left",
            border_style=self.colors['border'],
            box=box.ROUNDED,
            padding=(0, 1),
            width=panel_width
        )
        
        self.console.print(panel)
        self._last_output_had_newline = True
    
    def display_exit_panel(self, context_usage: str = "", cost: str = ""):
        """Show exit panel with consistent spacing"""
        # Ensure we're on a new line before displaying the goodbye box
        print()  # Force a new line before the goodbye box
        
        body = Text()
        body.append("goodbye!", style=f"bold {self.colors['orange']}")
        body.append("\nsession ended. thanks for using hakken code.", style=self.colors['light_gray'])
        
        # Add usage stats if available
        if context_usage or cost:
            body.append("\n", style="")  # Single blank line before stats
            if context_usage:
                body.append(f"context: {context_usage}", style=self.colors['gray'])
            if cost and context_usage:
                body.append("\n", style="")  # Line break between stats
            if cost:
                cost_str = str(cost)
                if not cost_str.strip().startswith("$"):
                    cost_str = "$" + cost_str
                body.append(f"cost: {cost_str}", style=self.colors['gray'])
                
        # Get terminal width and make panel responsive
        terminal_width = self.console.size.width
        panel_width = min(60, terminal_width - 4)  # Leave some margin
        
        panel = Panel(
            body,
            border_style=self.colors['orange'],
            box=box.ROUNDED,  # Back to rounded corners as requested
            padding=(0, 1),  # Match other panels - no vertical padding
            width=panel_width
        )
        
        self.console.print(panel)
        self._last_output_had_newline = True
    
    def print_simple_message(self, message: str, prefix: str = ""):
        """Compatibility method for simple message printing"""
        if message and message.strip():
            self._ensure_spacing_before_output()
            if prefix:
                text = Text()
                text.append(f"{prefix} ", style=f"bold {self.colors['blue']}")
                text.append(message, style=self.colors['light_gray'])
                self.console.print(text)
            else:
                self.console.print(message, style=self.colors['light_gray'])
            self._mark_output_with_newline(message)
    
    def show_tool_execution(self, tool_name: str, args: dict, success: bool, result: str = ""):
        """Show tool execution results - stop spinner and only show failures"""
        # Stop the spinner first (whether success or failure)
        self.stop_spinner()
        
        if not success:
            # Only show failures
            self._ensure_spacing_before_output()
            error_text = Text()
            error_text.append("❌ ", style=self.colors['red'])
            error_text.append(f"{tool_name} failed", style=f"bold {self.colors['red']}")
            if result and result.strip():
                error_msg = result[:150] + ('...' if len(result) > 150 else '')
                error_text.append(f": {error_msg}", style=self.colors['light_gray'])
            self.console.print(error_text)
            self._last_output_had_newline = True

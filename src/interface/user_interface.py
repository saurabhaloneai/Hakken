
from typing import Optional, List
from rich.console import Console
from rich import box

from .responsive_config import ResponsiveConfig
from .theme import UITheme
from .components import InputHandler, DisplayManager
from .chat_input_handler import ChatInputHandler


class UserInterface:
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.responsive = ResponsiveConfig(self.console)
        self.input_handler = InputHandler(self.console)
        self.display_manager = DisplayManager(self.console)
        self.chat_handler = ChatInputHandler(self.console)
        self._interrupt_callbacks = []
    
    def update_responsive_config(self) -> None:
        self.responsive = ResponsiveConfig(self.console)
        self.input_handler.responsive = self.responsive
        self.display_manager.responsive = self.responsive
        self.chat_handler.conversation.responsive = self.responsive
    
    async def get_user_input(self, prompt: str = "Enter: ") -> str:
        return await self.input_handler.get_user_input(prompt)
    
    async def get_chat_input(self, prompt: str = "What would you like me to help you with?") -> str:
        """Get user input in Claude-like chat interface where input becomes conversation history"""
        return await self.chat_handler.get_chat_input(prompt)
    
    def display_assistant_response_in_chat(self, content: str) -> None:
        """Display assistant response as part of chat conversation"""
        self.chat_handler.display_assistant_response(content)
    
    def clear_chat_conversation(self) -> None:
        """Clear the chat conversation history"""
        self.chat_handler.clear_conversation()
    
    def redisplay_chat_conversation(self) -> None:
        """Redisplay the entire chat conversation"""
        self.chat_handler.redisplay_conversation()
    
    async def wait_for_user_approval(self, content: str, emoji: str = UITheme.ROBOT) -> tuple[bool, str]:
        return await self.input_handler.wait_for_user_approval(content, emoji)
    
    async def wait_for_enhanced_approval(self, content: str, tool_name: str, args: dict, 
                                       options: dict, emoji: str = UITheme.ROBOT) -> tuple[str, dict, str]:
        return await self.input_handler.wait_for_enhanced_approval(content, tool_name, args, options, emoji)
    
    async def get_choice_input(self, prompt: str, choices: List[str], case_sensitive: bool = False) -> Optional[str]:
        return await self.input_handler.get_choice_input(prompt, choices, case_sensitive)
    
    def print_assistant_message(self, content: str, emoji: str = UITheme.ROBOT, use_chat: bool = False) -> None:
        """Print assistant message - can use either traditional or chat interface"""
        if use_chat:
            self.display_assistant_response_in_chat(content)
        else:
            self.display_manager.print_assistant_message(content, emoji)
    
    def print_simple_message(self, message: str, emoji: str = "") -> None:
        self.display_manager.print_simple_message(message, emoji)
    
    def print_error(self, error_message: str, emoji: str = UITheme.ERROR_X) -> None:
        self.display_manager.print_error(error_message, emoji)
    
    def print_success(self, success_message: str, emoji: str = UITheme.SUCCESS_CHECK) -> None:
        self.display_manager.print_success(success_message, emoji)
    
    def print_info(self, info_message: str, emoji: str = UITheme.INFO_I) -> None:
        self.display_manager.print_info(info_message, emoji)
    
    def print_warning(self, warning_message: str, emoji: str = UITheme.WARNING_EXCL) -> None:
        self.display_manager.print_warning(warning_message, emoji)
    
    def start_stream_display(self, refresh_rate: int = 10) -> None:
        self.display_manager.start_stream_display(refresh_rate)
    
    def stop_stream_display(self) -> None:
        self.display_manager.stop_stream_display()
    
    def print_streaming_content(self, chunk: str) -> None:
        self.display_manager.print_streaming_content(chunk)
    
    def get_stream_buffer(self) -> str:
        return self.display_manager.get_stream_buffer()
    
    def clear_stream_buffer(self) -> None:
        self.display_manager.clear_stream_buffer()
    
    async def confirm_action(self, action_description: str) -> tuple[bool, str]:
        return await self.wait_for_user_approval(action_description)
    
    def show_tool_execution(self, tool_name: str, tool_args: dict, success: bool = True, result: str = "") -> None:
        status = "success" if success else "error"
        self.display_manager.display_tool_status(tool_name, status, tool_args, result)
    
    def show_preparing_tool(self, tool_name: str, tool_args: dict) -> None:
        self.display_manager.display_tool_status(tool_name, "working", tool_args)
    
    def display_todos(self, todos: List, emoji: str = UITheme.TODO_LIST) -> None:
        self.display_manager.display_todos(todos, emoji)
    
    def display_separator(self, title: str = "") -> None:
        self.display_manager.display_separator(title)
    
    def display_welcome_header(self) -> None:
        if self.responsive.is_very_narrow:
            self.console.print(f"[bold {UITheme.PRIMARY}]{UITheme.ROBOT} Hakken[/bold {UITheme.PRIMARY}]")
            self.console.print(f"[{UITheme.ACCENT}]Ready![/{UITheme.ACCENT}]")
        elif self.responsive.is_narrow:
            self.console.print(f"\n[bold {UITheme.PRIMARY}]{UITheme.ROBOT} Welcome to Hakken[/bold {UITheme.PRIMARY}]")
            self.console.print(f"[{UITheme.MUTED}]AI Agent System[/{UITheme.MUTED}]")
            self.console.print(f"[{UITheme.ACCENT}]Ready to help![/{UITheme.ACCENT}]\n")
        else:
            from rich.panel import Panel
            
            content = (
                f"[bold {UITheme.PRIMARY}]Welcome to Hakken[/bold {UITheme.PRIMARY}]\n"
                f"[{UITheme.MUTED}]a agent which need too much context lenght[/{UITheme.MUTED}]\n\n"
                f"[{UITheme.ACCENT}]Ready to assist with your tasks![/{UITheme.ACCENT}]"
            )
            
            panel_width = self.responsive.get_panel_width(preferred_width=50)
            padding = (1, 2)
            
            welcome_panel = Panel(
                content,
                title=f"{UITheme.ROBOT} System Ready",
                box=box.ROUNDED,
                border_style=UITheme.SUCCESS,
                width=panel_width,
                padding=padding
            )
            self.console.print(welcome_panel)
    
    def display_context_info(self, context_usage: str, total_cost: str) -> None:
        if self.responsive.is_very_narrow:
            info_text = f"[{UITheme.MUTED}]{context_usage}% | ${total_cost}[/{UITheme.MUTED}]"
        elif self.responsive.is_narrow:
            info_text = f"[{UITheme.MUTED}]Ctx: {context_usage}% | Cost: ${total_cost}[/{UITheme.MUTED}]"
        else:
            info_text = f"[{UITheme.MUTED}]Context: {context_usage}% | Cost: ${total_cost}[/{UITheme.MUTED}]"
        
        self.console.print(f"\n{info_text}\n")
    
    def get_terminal_info(self) -> dict:
        return {
            'width': self.responsive.width,
            'height': self.responsive.height,
            'is_narrow': self.responsive.is_narrow,
            'is_very_narrow': self.responsive.is_very_narrow,
            'is_wide': self.responsive.is_wide,
            'is_very_wide': self.responsive.is_very_wide,
            'is_short': self.responsive.is_short
        }
    
    def display_terminal_info(self) -> None:
        info = self.get_terminal_info()
        
        size_info = f"Terminal: {info['width']}×{info['height']}"
        
        responsive_state = []
        if info['is_very_narrow']:
            responsive_state.append("very narrow")
        elif info['is_narrow']:
            responsive_state.append("narrow")
        elif info['is_very_wide']:
            responsive_state.append("very wide")
        elif info['is_wide']:
            responsive_state.append("wide")
        else:
            responsive_state.append("normal")
        
        if info['is_short']:
            responsive_state.append("short")
        
        state_text = ", ".join(responsive_state)
        
        debug_text = f"[{UITheme.MUTED}]{size_info} ({state_text})[/{UITheme.MUTED}]"
        self.console.print(debug_text)
    
    def start_interrupt_mode(self):
        """Start interrupt mode (no-op - interrupt system removed)"""
        pass
    
    def stop_interrupt_mode(self):
        """Stop interrupt mode (no-op - interrupt system removed)"""
        pass
    
    def add_interrupt_callback(self, callback):
        """Add interrupt callback (no-op - interrupt system removed)"""
        pass
    
    async def check_for_interrupts(self) -> Optional[str]:
        """Check for interrupts (no-op - interrupt system removed)"""
        return None

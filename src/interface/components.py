from typing import Optional, List
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.rule import Rule
from rich import box

from .responsive_config import ResponsiveConfig
from .theme import UITheme


class InputHandler:
    
    def __init__(self, console: Console):
        self.console = console
        self.responsive = ResponsiveConfig(console)
    
    async def get_user_input(self, prompt: str = "Enter: ") -> str:
        self.console.print(f"\n[bold {UITheme.PRIMARY}]● {prompt}[/bold {UITheme.PRIMARY}]")
        
        try:
            user_input = input("❯ ").strip()
            if user_input:
                self.console.print(f"[{UITheme.MUTED}]◯ Processing your request...[/{UITheme.MUTED}]")
            return user_input
        except (KeyboardInterrupt, EOFError):
            raise KeyboardInterrupt()
    
    async def wait_for_enhanced_approval(self, content: str, tool_name: str, args: dict, 
                                       options: dict, emoji: str = UITheme.ROBOT) -> tuple[str, dict, str]:
        display_content = self.responsive.truncate_text(content) if self.responsive.is_very_narrow else content
        
        if self.responsive.is_narrow:
            self.console.print(f"\n{emoji} [bold {UITheme.WARNING}]Tool Execution Request[/bold {UITheme.WARNING}]")
            self.console.print(f"[{UITheme.PRIMARY}]{display_content}[/{UITheme.PRIMARY}]")
        else:
            panel_width = self.responsive.get_panel_width(preferred_width=70)
            enhanced_content = self._enhance_command_description(display_content)
            
            approval_panel = Panel(
                f"[bold {UITheme.PRIMARY}]Tool: {tool_name}[/bold {UITheme.PRIMARY}]\n\n"
                f"{enhanced_content}\n",
                title=f"{emoji} Execution Request",
                box=box.ROUNDED,
                border_style=UITheme.WARNING,
                width=panel_width,
                padding=(1, 2)
            )
            self.console.print(approval_panel)
        
        available_options = []
        if options.get("allow_accept", True):
            available_options.append("[bold]'accept'[/bold] - Execute as-is")
        if options.get("allow_edit", False):
            available_options.append("[bold]'edit'[/bold] - Modify arguments")
        if options.get("allow_respond", True):
            available_options.append("[bold]'respond'[/bold] - Add instructions")
        if options.get("allow_ignore", False):
            available_options.append("[bold]'ignore'[/bold] - Skip this tool")
        
        self.console.print(f"[{UITheme.MUTED}]Options:\n" + "\n".join([f"• {opt}" for opt in available_options]) + "[/{UITheme.MUTED}]\n")
        
        while True:
            user_input = await self.get_user_input("Your choice")
            user_input_lower = user_input.lower().strip()
            
            if "accept" in user_input_lower or user_input_lower == "a":
                return "accept", args, ""
            
            elif "edit" in user_input_lower or user_input_lower == "e":
                if not options.get("allow_edit", False):
                    self.console.print(f"[{UITheme.ERROR}]Edit not allowed for this tool[/{UITheme.ERROR}]")
                    continue
                return await self._handle_edit_args(args)
            
            elif "respond" in user_input_lower or user_input_lower == "r":
                if not options.get("allow_respond", True):
                    self.console.print(f"[{UITheme.ERROR}]Response not allowed for this tool[/{UITheme.ERROR}]")
                    continue
                response = await self.get_user_input("Your response/instructions")
                return "respond", args, response
            
            elif "ignore" in user_input_lower or user_input_lower == "i":
                if not options.get("allow_ignore", False):
                    self.console.print(f"[{UITheme.ERROR}]Ignore not allowed for this tool[/{UITheme.ERROR}]")
                    continue
                return "ignore", args, "Tool execution skipped by user"
            
            else:
                valid_choices = [opt.split("'")[1] for opt in available_options]
                self.console.print(f"[{UITheme.ERROR}]Invalid choice. Choose from: {', '.join(valid_choices)}[/{UITheme.ERROR}]")
    
    async def _handle_edit_args(self, args: dict) -> tuple[str, dict, str]:
        self.console.print(f"[{UITheme.INFO}]Current arguments:[/{UITheme.INFO}]")
        for key, value in args.items():
            if key != 'need_user_approve':
                self.console.print(f"  {key}: {value}")
        
        new_args = args.copy()
        
        while True:
            edit_input = await self.get_user_input("Edit (key=value) or 'done'")
            
            if edit_input.lower() == 'done':
                break
            
            if '=' in edit_input:
                key, value = edit_input.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                if key in new_args:
                    new_args[key] = value
                    self.console.print(f"[{UITheme.SUCCESS}]Updated {key} = {value}[/{UITheme.SUCCESS}]")
                else:
                    self.console.print(f"[{UITheme.WARNING}]Unknown argument: {key}[/{UITheme.WARNING}]")
            else:
                self.console.print(f"[{UITheme.ERROR}]Format: key=value[/{UITheme.ERROR}]")
        
        return "accept", new_args, "Arguments edited by user"

    async def wait_for_user_approval(self, content: str, emoji: str = UITheme.ROBOT) -> tuple[bool, str]:
        display_content = self.responsive.truncate_text(content) if self.responsive.is_very_narrow else content
        
        if self.responsive.is_narrow:
            self.console.print(f"\n{emoji} [bold {UITheme.WARNING}]Confirmation Required[/bold {UITheme.WARNING}]")
            self.console.print(f"[{UITheme.PRIMARY}]{display_content}[/{UITheme.PRIMARY}]")
            self.console.print(f"[{UITheme.MUTED}]Type 'yes' to approve or 'no' to decline[/{UITheme.MUTED}]\n")
        else:
            panel_width = self.responsive.get_panel_width(preferred_width=70)
            
            enhanced_content = self._enhance_command_description(display_content)
            
            approval_panel = Panel(
                f"[bold {UITheme.PRIMARY}]Command Execution Request[/bold {UITheme.PRIMARY}]\n\n"
                f"{enhanced_content}\n\n"
                f"[{UITheme.MUTED}]• Type [bold]'yes'[/bold] to approve and execute\n"
                f"• Type [bold]'no'[/bold] to decline and cancel[/{UITheme.MUTED}]",
                title=f"{emoji} Confirmation Required",
                box=box.ROUNDED,
                border_style=UITheme.WARNING,
                width=panel_width,
                padding=(1, 2)
            )
            self.console.print(approval_panel)
        
        while True:
            user_input = await self.get_user_input("Your choice")
            user_input_lower = user_input.lower().strip()
            
            if "yes" in user_input_lower or user_input_lower == "y":
                return True, ""
            elif "no" in user_input_lower or user_input_lower == "n":
                return False, user_input
            else:
                error_msg = "Please answer 'yes' or 'no'" if self.responsive.is_very_narrow else "Invalid input. Please answer 'yes' or 'no'"
                self.console.print(f"[{UITheme.ERROR}]{error_msg}[/{UITheme.ERROR}]")
    
    def _enhance_command_description(self, content: str) -> str:
        try:
            if "Tool:" in content and "command" in content:
                lines = content.split('\n')
                tool_line = ""
                command = ""
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('Tool:'):
                        tool_line = line
                        if "'command':" in line:
                            start = line.find("'command':") + len("'command':")
                            rest = line[start:].strip()
                            if rest.startswith("'"):
                                end = rest.find("'", 1)
                                if end != -1:
                                    command = rest[1:end]
                            elif rest.startswith('"'):
                                end = rest.find('"', 1)
                                if end != -1:
                                    command = rest[1:end]
                
                if command:
                    explanation = self._explain_command(command)
                    
                    formatted_content = []
                    formatted_content.append(f"[bold {UITheme.INFO}]Command:[/bold {UITheme.INFO}] [cyan]{command}[/cyan]")
                    formatted_content.append(f"[bold {UITheme.SUCCESS}]Purpose:[/bold {UITheme.SUCCESS}] {explanation}")
                    
                    if tool_line:
                        tool_name = tool_line.replace('Tool:', '').split(',')[0].strip()
                        formatted_content.append(f"[{UITheme.MUTED}]Tool: {tool_name}[/{UITheme.MUTED}]")
                    
                    return '\n'.join(formatted_content)
            
            lines = content.split('\n')
            formatted_content = []
            for line in lines:
                line = line.strip()
                if line.startswith('Tool:'):
                    tool_part = line.replace('Tool:', '').strip()
                    formatted_content.append(f"[bold {UITheme.INFO}]Tool:[/bold {UITheme.INFO}] {tool_part}")
                elif 'args:' in line.lower():
                    formatted_content.append(f"[{UITheme.MUTED}]{line}[/{UITheme.MUTED}]")
                else:
                    formatted_content.append(line)
            
            return '\n'.join(formatted_content)
            
        except Exception:
            return content
    
    def _explain_command(self, command: str) -> str:
        command = command.strip().lower()
        
        if command.startswith('echo '):
            text = command[5:].strip()
            return f"Print the text '{text}' to the terminal"
        
        elif command.startswith('touch '):
            files = command[6:].strip()
            if ' ' in files:
                return f"Create new empty files: {files}"
            else:
                return f"Create a new empty file '{files}'"
        
        elif command.startswith('mkdir '):
            dirs = command[6:].strip()
            if ' ' in dirs:
                return f"Create new directories: {dirs}"
            else:
                return f"Create a new directory '{dirs}'"
        
        elif command.startswith('rm '):
            target = command[3:].strip()
            if target.startswith('-rf '):
                return f"⚠️ Permanently delete directory and all contents: {target[4:]}"
            elif target.startswith('-r '):
                return f"⚠️ Delete directory and all contents: {target[3:]}"
            elif target.startswith('-f '):
                return f"⚠️ Force delete file: {target[3:]}"
            else:
                return f"Delete file: {target}"
        
        elif command.startswith('cp '):
            parts = command[3:].strip().split()
            if len(parts) >= 2:
                return f"Copy '{parts[0]}' to '{parts[-1]}'"
            else:
                return f"Copy files: {command[3:]}"
        
        elif command.startswith('mv '):
            parts = command[3:].strip().split()
            if len(parts) >= 2:
                return f"Move/rename '{parts[0]}' to '{parts[-1]}'"
            else:
                return f"Move files: {command[3:]}"
        
        elif command.startswith('ls '):
            path = command[3:].strip() or "current directory"
            return f"List files and directories in {path}"
        
        elif command == 'ls':
            return "List files and directories in current directory"
        
        elif command == 'pwd':
            return "Show current directory path"
        
        elif command.startswith('cd '):
            path = command[3:].strip()
            return f"Change to directory '{path}'"
        
        elif command.startswith('cat '):
            file = command[4:].strip()
            return f"Display contents of file '{file}'"
        
        elif command.startswith('grep '):
            return f"Search for text patterns: {command}"
        
        elif command.startswith('find '):
            return f"Search for files and directories: {command[5:]}"
        
        elif command.startswith('chmod '):
            return f"Change file permissions: {command[6:]}"
        
        elif command.startswith('chown '):
            return f"Change file ownership: {command[6:]}"
        
        elif command.startswith('curl '):
            return f"Download or request data from URL: {command[5:]}"
        
        elif command.startswith('wget '):
            return f"Download file from URL: {command[5:]}"
        
        elif command.startswith('git '):
            git_cmd = command[4:].strip()
            if git_cmd.startswith('add '):
                return f"Stage files for git commit: {git_cmd[4:]}"
            elif git_cmd.startswith('commit '):
                return f"Create git commit: {git_cmd[7:]}"
            elif git_cmd.startswith('push'):
                return "Push commits to remote repository"
            elif git_cmd.startswith('pull'):
                return "Pull changes from remote repository"
            elif git_cmd.startswith('clone '):
                return f"Clone git repository: {git_cmd[6:]}"
            else:
                return f"Execute git command: {git_cmd}"
        
        elif command.startswith('npm '):
            npm_cmd = command[4:].strip()
            if npm_cmd.startswith('install'):
                return f"Install Node.js packages: {npm_cmd}"
            elif npm_cmd.startswith('run '):
                return f"Run npm script: {npm_cmd[4:]}"
            else:
                return f"Execute npm command: {npm_cmd}"
        
        elif command.startswith('pip '):
            pip_cmd = command[4:].strip()
            if pip_cmd.startswith('install '):
                return f"Install Python package: {pip_cmd[8:]}"
            else:
                return f"Execute pip command: {pip_cmd}"
        
        elif command.startswith('python '):
            script = command[7:].strip()
            return f"Run Python script: {script}"
        
        elif command.startswith('node '):
            script = command[5:].strip()
            return f"Run Node.js script: {script}"
        
        else:
            return f"Execute shell command: {command}"
    
    async def get_choice_input(self, prompt: str, choices: List[str], case_sensitive: bool = False) -> Optional[str]:
        if self.responsive.is_narrow:
            self.console.print(f"\n[bold {UITheme.PRIMARY}]{prompt}[/bold {UITheme.PRIMARY}]")
            for choice in choices:
                self.console.print(f"  • [{UITheme.ACCENT}]{choice}[/{UITheme.ACCENT}]")
            self.console.print()
        else:
            if len(choices) > 4:
                choice_text = "\n".join([f"• [{UITheme.ACCENT}]{choice}[/{UITheme.ACCENT}]" for choice in choices])
            else:
                choice_text = " | ".join([f"[{UITheme.ACCENT}]{choice}[/{UITheme.ACCENT}]" for choice in choices])
            
            panel_width = self.responsive.get_panel_width(preferred_width=60)
            
            choice_panel = Panel(
                f"[bold {UITheme.PRIMARY}]{prompt}[/bold {UITheme.PRIMARY}]\n\n"
                f"Options: {choice_text}",
                box=box.ROUNDED,
                border_style=UITheme.INFO,
                width=panel_width,
                padding=(1, 2)
            )
            self.console.print(choice_panel)
        
        while True:
            user_input = await self.get_user_input("Your choice")
            
            if case_sensitive:
                if user_input in choices:
                    return user_input
            else:
                user_input_lower = user_input.lower()
                choices_lower = [choice.lower() for choice in choices]
                if user_input_lower in choices_lower:
                    return choices[choices_lower.index(user_input_lower)]
            
            choices_display = ', '.join(choices)
            if self.responsive.is_narrow and len(choices_display) > 40:
                choices_display = f"{len(choices)} options above"
            
            self.console.print(f"[{UITheme.ERROR}]Invalid choice. Choose from: {choices_display}[/{UITheme.ERROR}]")


class DisplayManager:
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.responsive = ResponsiveConfig(self.console)
        self._live_display = None
        self._stream_buffer = ""
        self._is_streaming = False
    
    def print_assistant_message(self, content: str, emoji: str = UITheme.ROBOT) -> None:
        if content is None:
            return
        
        content = content.strip() if content else ""
        if not content:  # Don't print anything if content is empty
            return
            
        if self.responsive.is_narrow:
            panel_width = self.responsive.get_panel_width(preferred_width=50)
            
            assistant_panel = Panel(
                Markdown(content),
                title=f"{emoji} Assistant",
                box=box.SIMPLE if self.responsive.is_very_narrow else box.ROUNDED,
                border_style=UITheme.PRIMARY,
                width=panel_width,
                padding=(0, 1) if self.responsive.is_very_narrow else (1, 1)
            )
        else:
            panel_width = self.responsive.get_panel_width(preferred_width=80)
            
            assistant_panel = Panel(
                Markdown(content),
                title=f"{emoji} Assistant",
                box=box.ROUNDED,
                border_style=UITheme.PRIMARY,
                width=panel_width,
                padding=(1, 2)
            )
        
        self.console.print(assistant_panel)
    
    def print_simple_message(self, message: str, emoji: str = "") -> None:
        if emoji:
            self.console.print(f"{emoji}")
        if message:
            display_message = message
            if self.responsive.is_narrow and len(message) > self.responsive.get_text_wrap_width():
                display_message = self.responsive.truncate_text(message)
            
            self.console.print(f"[{UITheme.MUTED}]{display_message}[/{UITheme.MUTED}]")
    
    def print_status_message(self, message: str, status: str = "info") -> None:
        color, emoji = UITheme.get_status_style(status)
        
        display_message = message
        if self.responsive.is_narrow:
            display_message = self.responsive.truncate_text(message, max_length=60)
        
        self.console.print(f"{emoji} [{color}]{display_message}[/{color}]")
    
    def print_error(self, error_message: str, emoji: str = UITheme.ERROR_X) -> None:
        self.print_status_message(error_message, "error")
    
    def print_success(self, success_message: str, emoji: str = UITheme.SUCCESS_CHECK) -> None:
        self.print_status_message(success_message, "success")
    
    def print_info(self, info_message: str, emoji: str = UITheme.INFO_I) -> None:
        self.print_status_message(info_message, "info")
    
    def print_warning(self, warning_message: str, emoji: str = UITheme.WARNING_EXCL) -> None:
        self.print_status_message(warning_message, "warning")
    
    def start_stream_display(self, refresh_rate: int = 10) -> None:
        self._is_streaming = True
        self._stream_buffer = ""
        
        # Show a simple working indicator instead of "Assistant:" header
        # The actual "Assistant:" will be shown by the chat interface
        self.console.print(f"\n[{UITheme.MUTED}]◯ Assistant:[/{UITheme.MUTED}] ", end="")
    
    def stop_stream_display(self) -> None:
        if self._is_streaming:
            self.console.print("\n")
        self._is_streaming = False
    
    def print_streaming_content(self, chunk: str) -> None:
        if self._is_streaming:
            self._stream_buffer += chunk
            print(chunk, end="", flush=True)
        else:
            print(chunk, end="", flush=True)
    
    def get_stream_buffer(self) -> str:
        return self._stream_buffer
    
    def clear_stream_buffer(self) -> None:
        self._stream_buffer = ""
    
    def display_separator(self, title: str = "") -> None:
        if title:
            display_title = title
            if self.responsive.is_narrow:
                display_title = self.responsive.truncate_text(title, max_length=30)
            rule = Rule(f"[bold {UITheme.ACCENT}]{display_title}[/bold {UITheme.ACCENT}]")
        else:
            rule = Rule(style=UITheme.MUTED)
        self.console.print(rule)
    
    def display_todos(self, todos: List, emoji: str = UITheme.TODO_LIST) -> None:
        if not todos:
            return
        
        if self.responsive.is_very_narrow:
            self._display_todos_compact(todos, emoji)
            return
        elif self.responsive.is_narrow:
            self._display_todos_narrow(todos, emoji)
            return
        else:
            self._display_todos_full(todos, emoji)
    
    def _display_todos_compact(self, todos: List, emoji: str) -> None:
        self.console.print(f"\n[bold {UITheme.PRIMARY}]{emoji} Tasks[/bold {UITheme.PRIMARY}]")
        
        for i, todo in enumerate(todos):
            status = todo.get('status', 'pending')
            task = todo.get('content', todo.get('task', 'No description'))
            priority = todo.get('priority', 'normal')
            
            status_icons = {
                "completed": f"[{UITheme.SUCCESS}]✓[/{UITheme.SUCCESS}]",
                "in_progress": f"[{UITheme.WARNING}]●[/{UITheme.WARNING}]",
                "pending": f"[{UITheme.INFO}]○[/{UITheme.INFO}]"
            }
            status_icon = status_icons.get(status, f"[{UITheme.MUTED}]?[/{UITheme.MUTED}]")
            
            priority_colors = {
                "high": UITheme.ERROR,
                "medium": UITheme.WARNING,
                "normal": UITheme.SUCCESS,
                "low": UITheme.MUTED
            }
            priority_color = priority_colors.get(priority, UITheme.MUTED)
            priority_indicator = f"[{priority_color}]{'!' if priority == 'high' else '·'}[/{priority_color}]"
            
            task_display = self.responsive.truncate_text(task, max_length=35)
            
            self.console.print(f"  {status_icon} {priority_indicator} {task_display}")
    
    def _display_todos_narrow(self, todos: List, emoji: str) -> None:
        self.console.print(f"\n[bold {UITheme.PRIMARY}]{emoji} Tasks[/bold {UITheme.PRIMARY}]")
        
        for todo in todos:
            status = todo.get('status', 'pending')
            task = todo.get('content', todo.get('task', 'No description'))
            priority = todo.get('priority', 'normal')
            
            status_icons = {
                "completed": f"[{UITheme.SUCCESS}]✓[/{UITheme.SUCCESS}]",
                "in_progress": f"[{UITheme.WARNING}]●[/{UITheme.WARNING}]",
                "pending": f"[{UITheme.INFO}]○[/{UITheme.INFO}]"
            }
            
            priority_colors = {
                "high": UITheme.ERROR,
                "medium": UITheme.WARNING, 
                "normal": UITheme.SUCCESS,
                "low": UITheme.MUTED
            }
            
            status_display = status_icons.get(status, f"[{UITheme.MUTED}]?[/{UITheme.MUTED}]")
            priority_color = priority_colors.get(priority, UITheme.MUTED)
            priority_display = f"[{priority_color}]{priority[0].upper()}[/{priority_color}]"
            
            task_display = self.responsive.truncate_text(task, max_length=50)
            
            self.console.print(f"  {status_display} [{priority_color}][{priority_display}][/{priority_color}] {task_display}")
    
    def _display_todos_full(self, todos: List, emoji: str) -> None:
        table = Table(
            show_header=True,
            header_style=f"bold {UITheme.PRIMARY}",
            border_style=UITheme.MUTED,
            box=box.SIMPLE_HEAD,
            title=f"[bold {UITheme.PRIMARY}]{emoji} Tasks[/bold {UITheme.PRIMARY}]",
            title_style=f"bold {UITheme.PRIMARY}"
        )
        
        if self.responsive.is_very_wide:
            table.add_column("", style="cyan", width=3, justify="center")
            table.add_column("Task", style="white", min_width=40)
            table.add_column("Priority", style="green", width=8, justify="center")
            table.add_column("ID", style=UITheme.MUTED, width=6, justify="center")
        else:
            table.add_column("", style="cyan", width=3, justify="center")
            table.add_column("Task", style="white", min_width=30)
            table.add_column("Pri", style="green", width=4, justify="center")
        
        status_icons = {
            "completed": f"[{UITheme.SUCCESS}]✓[/{UITheme.SUCCESS}]",
            "in_progress": f"[{UITheme.WARNING}]●[/{UITheme.WARNING}]",
            "pending": f"[{UITheme.INFO}]○[/{UITheme.INFO}]"
        }
        
        priority_colors = {
            "high": UITheme.ERROR,
            "medium": UITheme.WARNING,
            "normal": UITheme.SUCCESS,
            "low": UITheme.MUTED
        }
        
        for todo in todos:
            status = todo.get('status', 'pending')
            task = todo.get('content', todo.get('task', 'No description'))
            priority = todo.get('priority', 'normal')
            todo_id = todo.get('id', 'N/A')
            
            status_display = status_icons.get(status, f"[{UITheme.MUTED}]?[/{UITheme.MUTED}]")
            priority_color = priority_colors.get(priority, UITheme.MUTED)
            
            if self.responsive.is_very_wide:
                priority_display = f"[{priority_color}]{priority.title()}[/{priority_color}]"
                id_display = f"[{UITheme.MUTED}]{todo_id}[/{UITheme.MUTED}]"
                table.add_row(status_display, task, priority_display, id_display)
            else:
                priority_display = f"[{priority_color}]{priority[0].upper()}[/{priority_color}]"
                table.add_row(status_display, task, priority_display)
        
        self.console.print()
        self.console.print(table)
    
    def display_tool_status(self, tool_name: str, status: str, args: dict, result: str = "") -> None:
        status_color, status_symbol = UITheme.get_status_style(status)
        
        if self.responsive.is_very_narrow:
            args_text = f"{len(args)} args" if args else ""
            tool_display = self.responsive.truncate_text(tool_name, max_length=20)
        elif self.responsive.is_narrow:
            args_items = list(args.items())[:2]
            args_text = ", ".join([f"{k}={self._format_arg_value(v)[:25]}" for k, v in args_items])
            if len(args) > 2:
                args_text += "..."
            tool_display = self.responsive.truncate_text(tool_name, max_length=25)
        else:
            # For normal/wide displays, be more generous with argument display
            args_items = list(args.items())[:3]  # Show more arguments
            args_text = ", ".join([f"{k}={self._format_arg_value(v)}" for k, v in args_items])
            if len(args) > 3:
                args_text += "..."
            tool_display = tool_name
        
        status_line = f"{status_symbol} [{status_color}]{tool_display}[/{status_color}]"
        if args_text:
            status_line += f" [{UITheme.MUTED}]({args_text})[/{UITheme.MUTED}]"
        
        self.console.print(status_line)
        
        if result:
            result_color = UITheme.MUTED if status == "success" else UITheme.ERROR
            max_result_length = 60 if self.responsive.is_narrow else 100
            display_result = result[:max_result_length] + "..." if len(result) > max_result_length else result
            self.console.print(f"  [{result_color}]{display_result}[/{result_color}]")
    
    def _format_arg_value(self, value) -> str:
        """Format argument values for display, handling different types appropriately"""
        if isinstance(value, (list, dict)):
            # For complex structures, show a summary instead of truncating
            if isinstance(value, list):
                return f"[{len(value)} items]"
            elif isinstance(value, dict):
                return f"{{{len(value)} keys}}"
        else:
            # For simple values, allow more characters but still limit
            str_value = str(value)
            if len(str_value) <= 40:
                return str_value
            else:
                return str_value[:37] + "..."

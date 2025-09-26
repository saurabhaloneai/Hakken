import os
import sys
import termios
import tty
import select
from typing import Optional
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich import box
from interface.base_ui import BaseUI, Message


class InteractionUI(BaseUI):
    """Interaction UI class for user input, confirmations, and approvals"""
    
    async def get_user_input(self, prompt: str = "", add_to_history: bool = True) -> str:
        self._ensure_spacing_before_output()
        
        # Display prompt
        prompt_text = Text()
        prompt_text.append("> ", style=f"bold {self.colors['blue']}")
        self.console.print(prompt_text, end="")

        # Get input with better error handling
        try:
            user_input = input("").strip()
            
            # Filter out any escape sequences or control characters
            user_input = ''.join(char for char in user_input if ord(char) >= 32 or char in '\t\n')
            
            # If input is empty or just whitespace, return empty string
            if not user_input:
                return ""
                
        except (EOFError, KeyboardInterrupt):
            print()  # Add newline after interrupt
            return ""
        except Exception as e:
            self.display_error(f"Input error: {e}")
            return ""
            
        if user_input and add_to_history:
            self.conversation.append(Message('user', user_input))
            
        self._last_output_had_newline = True  # Input always ends with newline
        return user_input
    
    def start_assistant_response(self):
        self._ensure_spacing_before_output()
        self._is_streaming = True
        self._streaming_content = ""
    
    def stream_content(self, chunk: str):
        """Stream content exactly like Hakken - just print the content"""
        if self._is_streaming:
            self._streaming_content += chunk
            self.console.print(chunk, end="", style=self.colors['light_gray'])
            self._mark_output_with_newline(chunk)

    def pause_stream_display(self):
        """Temporarily pause display output (visual separation for instruction mode)."""
        if self._is_streaming:
            # Always add a newline when pausing stream (for tool execution)
            if self._streaming_content and self._streaming_content.strip():
                print()  # Force newline before pausing
            self._is_streaming = False
            # Do not save partial stream into history yet
            # Content remains in _streaming_content if needed for later
        self._last_output_had_newline = True

    def resume_stream_display(self):
        """Resume display output after instruction capture."""
        # Ensure clean continuation after tool execution
        self._ensure_spacing_before_output()
        self._is_streaming = True
    
    def finish_assistant_response(self):
        """Finish streaming and save to conversation"""
        if self._is_streaming and self._streaming_content:
            self.conversation.append(Message('assistant', self._streaming_content))
            # FIXED: Always ensure a newline after assistant response
            print()  # Force a newline after every assistant response
            self._streaming_content = ""
        self._is_streaming = False
        self._last_output_had_newline = True  # Mark that we now have a newline
    
    def capture_instruction(self) -> Optional[str]:
        """Prompt user in a clean input mode while streaming is paused.
        Returns the instruction string or None if empty.
        """
        try:
            prompt_text = Text()
            prompt_text.append("> ", style=f"bold {self.colors['pink']}")
            self.console.print(prompt_text, end="")
            text = input("").strip()
            return text if text else None
        except (KeyboardInterrupt, EOFError):
            return None
    
    async def confirm_action(self, message: str) -> bool | str:
        """User confirmation: returns True/False or "always".
        Default behavior: simple prompt (y/n/a). Set env HAKKEN_APPROVAL_UI=arrow to use ↑/↓ UI.
        Non-interactive environments auto-approve/deny per env defaults.
        """
        try:
            # non-interactive fallback (e.g., running inside editor without a tty)
            if not sys.stdin or not sys.stdin.isatty():
                auto_approve = os.environ.get("HAKKEN_AUTO_APPROVE", "").strip().lower()
                approval_default = os.environ.get("HAKKEN_APPROVAL_DEFAULT", "").strip().lower()
                if auto_approve in ("1", "true", "yes", "y") or approval_default == "y":
                    self.display_info("auto-approving (non-interactive). set HAKKEN_APPROVAL_DEFAULT=n to deny.")
                    return True
                self.display_info("auto-denying (non-interactive). set HAKKEN_AUTO_APPROVE=1 to allow.")
                return False

            # interactive prompt
            # stop spinner to avoid overlap
            if self._spinner_active:
                try:
                    self.stop_spinner()
                except Exception:
                    pass

            # suspend background ESC listener during modal
            try:
                pass  # No longer need to manage modal state
            except Exception:
                pass

            default_yes = os.environ.get("HAKKEN_APPROVAL_DEFAULT", "").strip().lower() == "y" or \
                           os.environ.get("HAKKEN_AUTO_APPROVE", "").strip().lower() in ("1", "true", "yes", "y")

            choices = ["yes", "no", "always"]
            selected = 0 if default_yes else 1

            prefer_arrow_ui = os.environ.get("HAKKEN_APPROVAL_UI", "").strip().lower() == "arrow"

            if not prefer_arrow_ui:
                # Simple one-shot prompt
                body = Text()
                body.append(message + "\n\n", style=self.colors['light_gray'])
                body.append("Options: ", style=self.colors['gray'])
                body.append("[y]es, [n]o, [a]lways\n\n", style=self.colors['light_gray'])
                default_label = "Y" if default_yes else "N"
                body.append(f"Press y/n/a and Enter (default {default_label}).", style=self.colors['gray'])
                title_text = Text()
                title_text.append("approval required", style=f"bold {self.colors['orange']}")

                # Make panel responsive
                terminal_width = self.console.size.width
                panel_width = min(80, terminal_width - 4)

                panel = Panel(
                    body,
                    title=title_text,
                    title_align="left",
                    border_style=self.colors['border'],
                    box=box.ROUNDED,
                    padding=(0, 1),
                    width=panel_width,
                )
                self.console.print(panel)

                prompt = Text()
                prompt.append("approve? ", style=f"bold {self.colors['blue']}")
                prompt.append("[y/n/a]: ", style=self.colors['gray'])
                self.console.print(prompt, end="")

                answer = input("").strip().lower()
                if not answer:
                    return True if default_yes else False
                if answer in ("y", "yes", "1"):
                    return True
                if answer in ("n", "no", "2"):
                    return False
                if answer in ("a", "always", "3"):
                    return "always"
                # Unrecognized -> default
                return True if default_yes else False

            # Arrow-key UI (optional)
            def render_panel(sel: int) -> Panel:
                body = Text()
                body.append(message + "\n\n", style=self.colors['light_gray'])
                body.append("use ↑/↓ to select, Enter to confirm.\n\n", style=self.colors['gray'])
                for idx, label in enumerate(choices):
                    prefix = "> " if idx == sel else "  "
                    style = f"bold {self.colors['white']}" if idx == sel else self.colors['white']
                    body.append(prefix + label + ("\n" if idx < len(choices)-1 else ""), style=style)
                title_text = Text()
                title_text.append("approval required", style=f"bold {self.colors['orange']}")
                # Make panel responsive to terminal width
                terminal_width = self.console.size.width
                panel_width = min(80, terminal_width - 4)
                
                return Panel(
                    body,
                    title=title_text,
                    title_align="left",
                    border_style=self.colors['border'],
                    box=box.ROUNDED,
                    padding=(0, 1),
                    width=panel_width,
                )

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                # Drain any pending input bytes before starting selection loop
                try:
                    while select.select([sys.stdin], [], [], 0)[0]:
                        _ = sys.stdin.read(1)
                except Exception:
                    pass
                with Live(render_panel(selected), console=self.console, refresh_per_second=30, transient=True) as live:
                    while True:
                        ch = sys.stdin.read(1)
                        if ch == "\x1b":
                            seq1 = sys.stdin.read(1)
                            if seq1 == "[":
                                seq2 = sys.stdin.read(1)
                                if seq2 == "A":  # up
                                    selected = (selected - 1) % len(choices)
                                elif seq2 == "B":  # down
                                    selected = (selected + 1) % len(choices)
                                # ignore left/right
                                live.update(render_panel(selected))
                                continue
                            else:
                                # standalone ESC: treat as cancel -> default selection
                                break
                        if ch in ("\r", "\n"):
                            break
                        if ch.lower() in ("1", "y"):
                            selected = 0
                            break
                        if ch.lower() in ("2", "n"):
                            selected = 1
                            break
                        if ch.lower() in ("3", "a"):
                            selected = 2
                            break
                        # any other key: re-render unchanged
                        live.update(render_panel(selected))
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

            # Re-arm ESC listener after approval selection
            try:
                pass  # No longer need to restart interrupt listener
            except Exception:
                pass
            finally:
                pass  # No longer need to manage _in_modal_prompt

            result = choices[selected]
            if result == "yes":
                return True
            if result == "no":
                return False
            return "always"
        except (KeyboardInterrupt, EOFError):
            return False
    
    async def wait_for_user_approval(self, message: str) -> tuple[bool, str]:
        """Wait for user approval - returns (approved, user_input)"""
        try:
            # Show current todos before asking for approval if we have any
            if self.todos:
                self.display_todos()
                
            result = await self.confirm_action(message)
            if result == "always":
                return True, "always approved"
            elif result is True:
                return True, "approved"
            else:
                return False, "denied"
        except Exception:
            return False, "denied"
    
    def show_preparing_tool(self, tool_name: str, args: dict):
        """Show context-aware spinner for tool preparation"""
        # Map tool names to appropriate spinner messages
        spinner_messages = {
            "file_editor": "Writing files...",
            "file_reader": "Reading files...",
            "grep_search": "Searching...",
            "cmd_runner": "Running command...",
            "web_search": "Searching web...",
            "todo_writer": "Updating tasks...",
            "task_memory": "Accessing memory...",
            "context_cropper": "Processing content...",
            "git_tools": "Git operation...",
            "task_delegator": "Delegating task..."
        }
        
        # Get appropriate message or default
        message = spinner_messages.get(tool_name, f"Using {tool_name}...")
        
        # Start spinner with context-aware message
        self.start_spinner(message, "dots")

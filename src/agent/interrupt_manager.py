import contextlib
import logging
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

from interface.user_interface import HakkenCodeUI
from agent.state_manager import StateManager


class InterruptManager:
    
    def __init__(self, ui_interface: HakkenCodeUI, state_manager: StateManager):
        self.ui_interface = ui_interface
        self.state_manager = state_manager
        self.logger = logging.getLogger(__name__)
    
    def start_interrupt_flow(self) -> None:
        with contextlib.suppress(Exception):
            self.ui_interface.display_interrupt_hint()
        with contextlib.suppress(Exception):
            self.ui_interface.start_interrupt_listener()
    
    def stop_interrupt_listener_safely(self) -> None:
        with contextlib.suppress(Exception):
            self.ui_interface.stop_interrupt_listener()
    
    def safe_poll_interrupt(self) -> Optional[str]:
        try:
            return self.ui_interface.poll_interrupt()
        except Exception:
            return None
    
    async def handle_stream_interruption(self) -> None:
        instruction = await self._capture_instruction_interactively()
        if instruction:
            with contextlib.suppress(Exception):
                self.ui_interface.start_spinner("Applying instruction...")
            self.state_manager.state.pending_user_instruction = instruction
    
    async def _capture_instruction_interactively(self) -> Optional[str]:
        try:
            self.ui_interface.pause_stream_display()
            self.ui_interface.flush_interrupts()
            
            instruction = self.ui_interface.wait_for_interrupt(
                timeout=self.state_manager.agent_config.INTERRUPT_TIMEOUT
            )
            
            if not instruction:
                self.stop_interrupt_listener_safely()
                instruction = self.ui_interface.capture_instruction()
                with contextlib.suppress(Exception):
                    self.ui_interface.start_interrupt_listener()
                    
            return instruction
        finally:
            with contextlib.suppress(Exception):
                self.ui_interface.resume_stream_display()
    
    def stop_spinner_safely(self) -> None:
        """Stop spinner safely with exception handling."""
        with contextlib.suppress(Exception):
            self.ui_interface.stop_spinner()
    
    def ensure_spinner_stopped(self, spinner_stopped: bool) -> bool:
        """Ensure spinner is stopped and return new state."""
        if not spinner_stopped:
            self.stop_spinner_safely()
            return True
        return spinner_stopped

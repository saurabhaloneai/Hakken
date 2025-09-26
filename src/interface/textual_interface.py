#!/usr/bin/env python3
"""
Textual interface entry point for Hakken AI Agent.
Connects the new HakkenCodeUI with the Agent class.
"""

import asyncio
import sys
import os
import signal
from core.agent import Agent
from interface.user_interface import HakkenCodeUI


class HakkenAgent:
    """Main agent wrapper that integrates the UI with the Agent."""
    
    def __init__(self):
        self.ui = HakkenCodeUI()
        self.agent = Agent()
        # Connect the UI to the agent
        self.agent._ui_manager = self.ui
        self._running = True
        
    async def run(self):
        """Main run loop for the agent."""
        try:
            # Display welcome header
            self.ui.display_welcome_header()
            
            
            # Start the agent
            await self.agent.start_Agent()
            
        except KeyboardInterrupt:
            # Clean shutdown without verbose messages
            pass
        except Exception as e:
            self.ui.display_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean shutdown
            
            # Get usage statistics for exit display
            context_usage = ""
            cost = ""
            
            try:
                context_usage = f"{self.agent._history_manager.current_context_window}%"
                cost = f"${self.agent._api_client.total_cost:.2f}"
            except Exception:
                # If there's any error getting usage data, just show the panel without it
                pass
            
            self.ui.display_exit_panel(context_usage=context_usage, cost=cost)


def run_textual_interface():
    """Entry point function called by the hakken command."""
    # Handle Ctrl+C gracefully
    def signal_handler(signum, frame):
        # Clean shutdown without verbose messages
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Create and run the agent
        hakken_agent = HakkenAgent()
        asyncio.run(hakken_agent.run())
    except KeyboardInterrupt:
        # Clean exit without messages
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_textual_interface()

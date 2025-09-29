#!/usr/bin/env python3
def main():
    
    import sys
    import os
    import asyncio
    import signal
    from core.agent import Agent
    from interface.user_interface import HakkenCodeUI
        

    class HakkenAgent:            
        def __init__(self):
            self.ui = HakkenCodeUI()
            self.agent = Agent()
            self.agent._ui_manager = self.ui
            self._running = True

        async def run(self):
            try:
                self.ui.display_welcome_header()
                await self.agent.start_agent()
                
            except KeyboardInterrupt:
                pass
            except Exception as e:
                self.ui.display_error(f"Unexpected error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                context_usage = ""
                cost = ""
                
                try:
                    context_usage = f"{self.agent._history_manager.current_context_window}%"
                    cost = f"${self.agent._api_client.total_cost:.2f}"
                except Exception:
                    pass
                
                self.ui.display_exit_panel(context_usage=context_usage, cost=cost)
    def signal_handler(signum, frame):
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    hakken_agent = HakkenAgent()
    asyncio.run(hakken_agent.run())

if __name__ == "__main__":
    main()

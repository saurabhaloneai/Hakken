import asyncio
import argparse
import sys
import os
from pathlib import Path

from hakken.core.factory import AgentFactory
from hakken.terminal_bridge import UIManager

async def run_agent():
    ui = UIManager()
    try:
        agent = AgentFactory.create_agent(ui_manager=ui)
        await agent.start_conversation()
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description="Hakken CLI - Command Line Interface for Hakken Application")
    parser.add_argument('--version', action='version', version='%(prog)s 1.0', help='Show the version of the application')
    parser.add_argument('--ui', choices=['terminal', 'react'], default='react', help='Choose UI mode (default: react)')
    
    args = parser.parse_args()
    
    if args.ui == 'react':
        # Launch React UI
        cli_file = Path(__file__).resolve()
        project_root = cli_file.parent.parent.parent
        app_tsx = project_root / "terminal_ui" / "src" / "index.tsx"
        
        if not app_tsx.exists():
            print(f"Error: Could not find terminal UI at {app_tsx}", file=sys.stderr)
            sys.exit(1)
            
        try:
            os.chdir(project_root)
            import subprocess
            subprocess.run(
                ["npx", "tsx", "--tsconfig", "terminal_ui/tsconfig.json", str(app_tsx)],
                check=True
            )
        except Exception as e:
            print(f"Error launching React UI: {e}")
            sys.exit(1)
    else:
        # Run Python Agent directly (Default)
        asyncio.run(run_agent())

if __name__ == "__main__":
    main()
import argparse
import sys
import os
from pathlib import Path


async def run_agent():
    from hakken.core.factory import AgentFactory
    from hakken.terminal_bridge import UIManager
    
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
    parser = argparse.ArgumentParser(description="Hakken CLI")
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('--ui', choices=['terminal', 'react'], default='react')
    args = parser.parse_args()
    
    if args.ui == 'react':
        cli_file = Path(__file__).resolve()
        project_root = cli_file.parent.parent.parent
        dist_js = project_root / "terminal_ui" / "dist" / "index.js"
        
        if dist_js.exists():
            cmd = ["node", str(dist_js)]
        else:
            app_tsx = project_root / "terminal_ui" / "src" / "index.tsx"
            if not app_tsx.exists():
                print("Error: Could not find terminal UI", file=sys.stderr)
                sys.exit(1)
            cmd = ["npx", "tsx", "--tsconfig", str(project_root / "terminal_ui" / "tsconfig.json"), str(app_tsx)]
            
        try:
            import subprocess
            subprocess.run(cmd, check=True, cwd=project_root, env={**os.environ, "HAKKEN_WORK_DIR": os.getcwd()})
        except Exception as e:
            print(f"Error launching React UI: {e}")
            sys.exit(1)
    else:
        import asyncio
        asyncio.run(run_agent())

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Main entry point for Hakken AI Agent.
Provides Textual-based interface.
"""

import sys
import os

# Add the src directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

def main():
    """Main entry point - launches the Textual interface."""
    try:
        # Import and run the textual interface
        from interface.textual_interface import run_textual_interface
        run_textual_interface()
    except ImportError as e:
        print("❌ Required dependencies not installed.")
        print("Install with: uv sync")
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting Hakken Agent: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

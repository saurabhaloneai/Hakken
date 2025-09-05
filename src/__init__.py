__version__ = "0.1.0"
__author__ = "Saurabh"
__description__ = "Component-wise AI Agent"

def cli():
    """Entry point for the hakken CLI application"""
    from .main import cli as main_cli
    return main_cli()

__all__ = ["cli", "__version__"]
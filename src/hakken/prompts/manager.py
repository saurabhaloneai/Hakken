from abc import ABC, abstractmethod
import os
from pathlib import Path

from hakken.prompts.environment import get_environment_info
from hakken.prompts.system_rules import get_system_rules


def load_hakken_instructions() -> str:
    hakken_path = Path(os.getcwd()) / "Hakken.md"
    if not hakken_path.exists():
        return ""
    content = hakken_path.read_text().strip()
    return f"\n\n## Project Instructions (from Hakken.md)\n{content}" if content else ""


class BasePromptManager(ABC):
    @abstractmethod
    def get_system_prompt(self) -> None:
        pass


class PromptManager(BasePromptManager):
    def __init__(self):
        pass

    def get_system_prompt(self) -> str:
        return f"""
        {get_system_rules()}
        {get_environment_info()}
        {load_hakken_instructions()}
        """.strip()
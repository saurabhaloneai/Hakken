import pytest
from hakken.prompts.manager import PromptManager

@pytest.fixture
def prompt_manager():
    return PromptManager()

def test_environment_prompt(prompt_manager):
    result = prompt_manager.get_environment_prompt()
    assert result is not None
    assert isinstance(result, str)

def test_reminder_prompt(prompt_manager):
    result = prompt_manager.get_reminder_prompt()
    assert result is not None
    assert isinstance(result, str)

def test_system_rules_prompt(prompt_manager):
    result = prompt_manager.get_system_rules_prompt()
    assert result is not None
    assert isinstance(result, str)
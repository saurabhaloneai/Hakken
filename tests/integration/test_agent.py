import pytest
from hakken.core.agent import Agent

@pytest.fixture
def agent():
    return Agent()

def test_agent_initialization(agent):
    assert agent is not None
    assert isinstance(agent, Agent)

def test_agent_functionality(agent):
    # Assuming the agent has a method called 'perform_action'
    result = agent.perform_action("test_action")
    assert result is not None
    assert result == "expected_result"  # Replace with actual expected result

def test_agent_history_management(agent):
    initial_history_length = len(agent.history)
    agent.perform_action("test_action")
    assert len(agent.history) == initial_history_length + 1

def test_agent_error_handling(agent):
    with pytest.raises(ValueError):
        agent.perform_action("invalid_action")  # Replace with actual invalid action
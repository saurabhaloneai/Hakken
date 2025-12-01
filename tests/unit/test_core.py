import pytest
from hakken.core.agent import Agent
from hakken.core.client import Client
from hakken.core.factory import Factory

@pytest.fixture
def setup_agent():
    agent = Agent()
    return agent

@pytest.fixture
def setup_client():
    client = Client()
    return client

def test_agent_initialization(setup_agent):
    assert setup_agent is not None
    assert isinstance(setup_agent, Agent)

def test_client_initialization(setup_client):
    assert setup_client is not None
    assert isinstance(setup_client, Client)

def test_factory_create_agent():
    agent = Factory.create_agent()
    assert agent is not None
    assert isinstance(agent, Agent)

def test_factory_create_client():
    client = Factory.create_client()
    assert client is not None
    assert isinstance(client, Client)
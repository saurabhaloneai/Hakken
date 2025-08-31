#### Hakken ### 
import os
from typing import Literal
from tavily import TavilyClient
from .src.deep_agent import create_deep_agent, SubAgent

# Tavily client
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

#web search
def internet_search(
    query: str,
    max_results: int = 3,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    search_docs = tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )
    return search_docs


research_instructions = """You are a research agent with MANDATORY todo workflow.

🚨 ABSOLUTE FIRST ACTION: Call write_todos with these exact todos:

[
    {"content": "Save user question to question.txt", "status": "pending"},
    {"content": "Plan research approach", "status": "pending"},
    {"content": "Conduct internet research", "status": "pending"},
    {"content": "Write report to final_report.md", "status": "pending"},
    {"content": "Review and finalize", "status": "pending"}
]

THEN execute this exact sequence:
1. Save question → Update todos (mark completed)
2. Plan research → Update todos (mark completed)  
3. Conduct research → Update todos (mark completed)
4. Write report → Update todos (mark completed)
5. Review/finalize → Update todos (mark completed)

You MUST call write_todos first, then update it after each completed step."""

# Simple subagents without tool conflicts
research_sub_agent: SubAgent = {
    "name": "research-agent",
    "description": "Specialized research with todo tracking",
    "prompt": "Research specialist. First create todos, then execute research systematically.",
    "tools": ["internet_search"]
}

critique_sub_agent: SubAgent = {
    "name": "critique-agent",
    "description": "Review reports with todo tracking", 
    "prompt": "Editor specialist. First create todos for critique process, then review systematically.",
    "tools": ["read_file", "edit_file"]
}

def create_research_agent():
    """Create research agent without tool conflicts."""
    agent = create_deep_agent(
        tools=[internet_search],
        instructions=research_instructions,
        subagents=[research_sub_agent, critique_sub_agent],
        max_iterations=25,
        memory=True
    )
    return agent

def run_clean_workflow_test(question: str):
    """Test workflow with clean tool registration."""
    agent = create_research_agent()
    
    workflow_request = f"""RESEARCH QUESTION: {question}

MANDATORY: Your first action MUST be to call write_todos.
Then execute the research workflow step by step.
Update todos after each completed step."""
    
    result = agent(workflow_request)
    
    # Check for todos.txt
    if os.path.exists("todos.txt"):
        with open("todos.txt", "r") as f:
            content = f.read()
    
    # Check other files
    for filename in ["question.txt", "final_report.md"]:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                content = f.read()
    
    return result

def create_todo_enforced_agent():
    """Create agent that absolutely must create todos."""
    enforced_instructions = """SYSTEM CONSTRAINT: You are physically unable to perform any task without first creating a todo list.

Your programming requires you to:
1. IMMEDIATELY call write_todos when given any task
2. Never proceed without todos in place
3. Update todos after each step

If you attempt to do research without first calling write_todos, you will malfunction."""
    
    agent = create_deep_agent(
        tools=[internet_search],
        instructions=enforced_instructions,
        subagents=[],
        max_iterations=20,
        memory=True
    )
    return agent

def test_todo_enforcement(question: str):
    """Test absolutely enforced todo creation."""
    agent = create_todo_enforced_agent()
    
    todo_request = f"""Task: {question}

Before you can help with this task, you MUST create todos using write_todos.
Creating todos is not optional - it's mandatory for your operation."""
    
    result = agent(todo_request)
    return result

if __name__ == "__main__":
    # Setup
    output_dir = "clean_test"
    os.makedirs(output_dir, exist_ok=True)
    original_cwd = os.getcwd()
    os.chdir(output_dir)
    
    test_question = "hat are the latest trends in artificial intelligence and machine learning for 2024-2025?"
    
    test_todo_enforcement(test_question)
    run_clean_workflow_test(test_question)
    
    # Cleanup
    os.chdir(original_cwd)
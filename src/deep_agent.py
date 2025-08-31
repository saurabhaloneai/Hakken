import os
from typing import Any, Callable, List, Optional, Sequence, Union, TypedDict, Literal, NotRequired
from prompts import BASE_PROMPT, TASK_DESCRIPTION_PREFIX, TASK_DESCRIPTION_SUFFIX, WRITE_TODOS_DESCRIPTION, EDIT_DESCRIPTION, TOOL_DESCRIPTION

class Todo(TypedDict):
    content: str
    status: Literal["pending", "in_progress", "completed"]

class DeepAgentState(TypedDict):
    todos: NotRequired[List[Todo]]
    files: NotRequired[dict[str, str]]
    messages: NotRequired[List[dict]]

class SubAgent(TypedDict):
    name: str
    description: str
    prompt: str
    tools: NotRequired[List[str]]
    model: NotRequired[Any]

def write_todos(todos: List[Todo]) -> str:
    with open("todos.txt", "w") as f:
        for todo in todos:
            f.write(f"[{todo['status']}] {todo['content']}\n")
    return f"✅ Updated todo list with {len(todos)} items"

def read_file(file_path: str, offset: int = 0, limit: int = 2000) -> str:
    """Read file with line numbers (cat -n format)."""
    with open(file_path, "r", encoding='utf-8') as f:
        lines = f.readlines()
    
    
    
    start_idx = offset
    end_idx = min(start_idx + limit, len(lines))
    
    
    
    result_lines = []
    for i in range(start_idx, end_idx):
        line_content = lines[i].rstrip('\n')
        if len(line_content) > 2000:
            line_content = line_content[:2000]
        line_number = i + 1
        result_lines.append(f"{line_number:6d}\t{line_content}")
    
    return "\n".join(result_lines)

def write_file(file_path: str, content: str) -> str:

    os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else ".", exist_ok=True)
    with open(file_path, "w", encoding='utf-8') as f:
        f.write(content)
    return f"Successfully wrote {len(content)} characters to '{file_path}'"

def edit_file(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
   
    with open(file_path, "r", encoding='utf-8') as f:
        content = f.read()
    
    if not replace_all:
        occurrences = content.count(old_string)
        if occurrences > 1:
            return f"Error: String '{old_string[:50]}...' appears {occurrences} times. Use replace_all=True or provide more context."
    
    if replace_all:
        new_content = content.replace(old_string, new_string)
        count = content.count(old_string)
        result_msg = f"successfully replaced {count} instance(s) in '{file_path}'"
    else:
        new_content = content.replace(old_string, new_string, 1)
        result_msg = f"successfully replaced string in '{file_path}'"
    
    with open(file_path, "w", encoding='utf-8') as f:
        f.write(new_content)
    
    return result_msg

def ls() -> str:
    
    files = os.listdir(".")
    if not files:
        return "Directory is empty"
    return "\n".join(sorted(files))

def create_task_tool(tools: List, instructions: str, subagents: List[SubAgent], model: Any):
    
    
    from loop import create_agent, Tool
    
    agents = {
        "general-purpose": create_agent(model, instructions, tools, max_iterations=15)
    }
    
    for subagent in subagents:
        sub_model = subagent.get("model", model)
        requested_tool_names = subagent.get("tools", [])
        
        if requested_tool_names:
            available_tools = []
            added_tool_names = set()
            
            for tool in tools:
                tool_name = None
                if hasattr(tool, 'name'):
                    tool_name = tool.name
                elif hasattr(tool, '__name__'):
                    tool_name = tool.__name__
                
                if tool_name in requested_tool_names and tool_name not in added_tool_names:
                    available_tools.append(tool)
                    added_tool_names.add(tool_name)
            
            sub_tools = available_tools
        else:
            sub_tools = tools
        
        agents[subagent["name"]] = create_agent(
            model=sub_model,
            prompt=subagent["prompt"], 
            tools=sub_tools,
            max_iterations=15
        )
    
    other_agents = [f"- {sa['name']}: {sa['description']}" for sa in subagents]
    description = TASK_DESCRIPTION_PREFIX.format(other_agents="\n".join(other_agents)) + TASK_DESCRIPTION_SUFFIX
    
    def task(description: str, subagent_type: str) -> str:
        if subagent_type not in agents:
            available = list(agents.keys())
            return f"Error: agent type '{subagent_type}' not found. Available types: {available}"
        
        agent = agents[subagent_type]
        result = agent(description)
        return result['final_text']
    
    return Tool("task", task, description)

def create_deep_agent(
    tools: Sequence[Union[Any, Callable]] = None,
    instructions: str = "",
    model: Optional[Any] = None,
    subagents: List[SubAgent] = None,
    builtin_tools: Optional[List[str]] = None,
    memory: bool = True,
    max_iterations: int = 15
):
    """Create a deep agent matching deepagents API exactly."""
    
    from loop import create_agent, AnthropicModel, Tool, ConversationMemory
    
    if model is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        model = AnthropicModel(api_key=api_key)
    
    prompt = instructions + BASE_PROMPT
    
    all_builtin_tools = [
        Tool("write_todos", write_todos, WRITE_TODOS_DESCRIPTION),
        Tool("write_file", write_file, "Write content to a file."),
        Tool("read_file", read_file, TOOL_DESCRIPTION),
        Tool("ls", ls, "List all files in current directory."),
        Tool("edit_file", edit_file, EDIT_DESCRIPTION)
    ]
    
    if builtin_tools is not None:
        tools_by_name = {tool.name: tool for tool in all_builtin_tools}
        built_in_tools = [tools_by_name[name] for name in builtin_tools if name in tools_by_name]
    else:
        built_in_tools = all_builtin_tools
    
    external_tools = []
    builtin_tool_names = {t.name for t in built_in_tools}
    
    if tools:
        for t in tools:
            tool_obj = None
            tool_name = None
            
            if isinstance(t, Tool):
                tool_obj = t
                tool_name = t.name
            elif callable(t):
                tool_name = getattr(t, "__name__", "unnamed_tool")
                tool_desc = getattr(t, "__doc__", "No description provided.")
                tool_obj = Tool(tool_name, t, tool_desc)
            
            if tool_name not in builtin_tool_names:
                external_tools.append(tool_obj)
    
    agent_tools = built_in_tools + external_tools
    
    tool_names = [t.name for t in agent_tools]
    unique_tool_names = set(tool_names)
    if len(tool_names) != len(unique_tool_names):
        seen = set()
        agent_tools = [t for t in agent_tools if not (t.name in seen or seen.add(t.name))]
    
    task_tool = create_task_tool(agent_tools, instructions, subagents or [], model)
    all_tools = agent_tools + [task_tool]
    
    agent_memory = ConversationMemory() if memory else None
    
    return create_agent(
        model=model,
        prompt=prompt,
        tools=all_tools,
        max_iterations=max_iterations,
        memory=agent_memory
    )
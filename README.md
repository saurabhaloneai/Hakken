# hakken

smart ai agent with planning and delegation

## what is hakken

hakken is an  ai agent that can break down complex tasks into steps, use tools, and have specialized sub-agents. it handles research, analysis, file management, and multi-step workflows.

## features

- automatic task planning for complex work
- tool integration (file ops, web search, custom tools)
- sub-agent delegation for specialized tasks
- persistent file system with auto-save to disk
- memory management and context optimization
- error handling with retry logic

## installation

from source (development):

```bash
git clone <your-repo-url>
cd hakken
pip install -e .
```

or with uv:

```bash
git clone <your-repo-url>
cd hakken  
uv pip install -e .
```

for production (when published):

```bash
pip install hakken
```

## quick start

```python
agent = create_deep_agent(
    tools=[tavily_search, web_scrape],
    instructions="""You are a comprehensive research and analysis agent with access to 
    advanced web search capabilities. Use your planning system to break down complex tasks,
    delegate to specialized sub-agents, and create thorough, well-researched outputs.""",
    subagents=[research_agent, analysis_agent, report_agent],
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    model="claude-sonnet-4-20250514"

```

## how it works

1. **planning** - automatically creates step-by-step plans for complex tasks
2. **execution** - runs each step using tools or delegates to sub-agents
3. **file system** - saves all outputs to organized folders on disk
4. **delegation** - routes specialized work to appropriate sub-agents

## built-in tools

- `plan_task` - create execution plans
- `write_file` - save files (auto-saves to disk)
- `read_file` - read files from memory
- `save_all_files` - batch save everything to disk
- `call_subagent` - delegate to sub-agents
- `ls` - list files
- `get_disk_status` - check file sync status

## file organization

files are automatically saved to organized folders:

```
deep_research_out/
├── reports/     # final outputs, reports
├── steps/       # step-by-step results  
├── plans/       # execution plans
├── sources/     # source materials
└── errors/      # error logs
```

## requirements

- python 3.8+
- anthropic api key
- anthropic python library

## api key setup

set your anthropic api key:

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

for web search functionality (optional):

```bash
export TAVILY_API_KEY="your-tavily-key"
```

or pass keys directly:

```python
agent = DeepAgent(api_key="your-anthropic-key")
```

get api keys:
- anthropic: https://console.anthropic.com/
- tavily (for web search): https://app.tavily.com/

## examples

check the examples/ folder for complete demos including research workflows, analysis tasks, and custom tool integration.

## license

mit
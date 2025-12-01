# hakken | 発見

>[!IMPORTANT]
>
> An interactive CLI AI agent(llm in feedback-loop) that suppose to help you with coding tasks.
> I have built this project to understand about how agents work and how to build effective agents.
> 
> Claude helped me here and there but mostly around UI design.


![img](./assets/hakken.png)

## core features

- **Multi-Provider LLM Support** - OpenAI integration and local llm using vLLM(coming soon...)
- **React/Ink Terminal UI** - Beautiful, interactive terminal interface with real-time updates
- **Autonomous Code Operations** - Read, edit, search, and manage files with AI assistance
- **Intelligent Code Search** - Semantic search with ChromaDB, grep patterns, and fuzzy file search
- **Git Integration** - Built-in git operations for status, commit, push, diff, and log
- **Memory System** - Repository-specific knowledge retention and retrieval
- **Task Management** - TODO tracking and autonomous task execution via subagents
- **Context Compression** - Efficient conversation history management

## project structure

```
hakken/
├── src/hakken/              # Main Python package
│   ├── core/                # Core agent components
│   │   ├── agent.py         # Main agent implementation
│   │   ├── factory.py       # Factory pattern for component creation
│   │   └── client.py        # LLM client wrapper
│   ├── tools/               # Comprehensive tool system
│   │   ├── filesystem/      # File operations (read, edit, delete, list_dir, search_replace)
│   │   ├── search/          # Code search (grep, file, semantic)
│   │   ├── execution/       # Terminal command execution
│   │   ├── git/             # Git operations (status, commit, push, diff, log)
│   │   ├── memory/          # Knowledge storage and retrieval
│   │   └── utilities/       # Task, TODO, and context compression
│   ├── prompts/             # System prompts and rules
│   ├── history/             # Conversation history management
│   ├── subagents/           # Autonomous subagent manager
│   ├── terminal_bridge.py   # UI manager and Python-UI bridge
│   └── cli.py               # CLI entry point
├── terminal_ui/             # React/Ink TypeScript UI
│   └── src/                 # UI source code
├── tests/                   # Test suite
└── pyproject.toml           # Project configuration
```

## how to run 

Clone the repository and install dependencies:

```bash
git clone https://github.com/saurabhaloneai/hakken.git
cd hakken
```

Install Python package:

```bash
uv pip install -e .
```

Install terminal UI dependencies:

```bash
cd terminal_ui
npm install
cd ..
```

### environment configuration

Create a `.env` file in the project root:

```env
# Required
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-oss-20b:free
# The unit is k
MODEL_MAX_TOKENS=250
COMPRESS_THRESHOLD=0.8
```

## usage

### Launch Hakken

```bash
# Default: Launch with React/Ink UI
hakken

# Show version
hakken --version
```

## tool system

Hakken provides a comprehensive set of tools for AI-powered code operations:

### file operations

- **read_file** - Read file contents with optional line range support
- **edit_file** - Create and modify files with full content replacement
- **search_replace** - Precise string-based find and replace
- **delete_file** - Safe file deletion with confirmation
- **list_dir** - Directory exploration and file listing

### code search

- **grep_search** - Pattern matching with regex support across files
- **file_search** - Fuzzy filename search to locate files quickly
- **semantic_search** - AI-powered semantic code search using ChromaDB embeddings

### terminal & execution

- **run_terminal_cmd** - Execute shell commands with real-time output streaming
- Command validation and security checks
- Working directory support

### git operations

- **git status** - Check repository status and changes
- **git commit** - Create commits with AI-generated or custom messages
- **git push** - Push changes to remote repository
- **git diff** - View file differences
- **git log** - Browse commit history

### memory & knowledge

- **add_memory** - Store repository-specific knowledge and context
- **list_memories** - Retrieve stored memories and insights
- Persistent knowledge base for better contextual understanding

### task management

- **todo** - Structured TODO list management
- **task** - Autonomous task execution via subagents
- **context_compression** - Intelligent conversation history compression


### tool manager

All tools are centrally registered and managed:

- Automatic tool discovery and validation
- JSON schema generation for LLM tool use
- Clean tool execution pipeline

### ui bridge

The terminal bridge (`terminal_bridge.py`) provides:
- WebSocket-based communication between Python agent and React UI
- Message streaming and event handling
- UI state management

### subagent system

Autonomous subagents can be spawned for:
- Complex multi-step tasks
- Parallel execution of independent operations
- Isolated contexts for specific objectives

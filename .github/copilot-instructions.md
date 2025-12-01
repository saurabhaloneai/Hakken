# Hakken Copilot Instructions

## Architecture Overview

Hakken is an autonomous AI coding agent with a **dual-process architecture**:
- **Python backend** (`src/hakken/`): Agent logic, tools, LLM client, history management
- **React/Ink frontend** (`terminal_ui/`): TypeScript terminal UI using React components

Communication uses a **JSON message bridge** via stdin/stdout. The `Bridge` class (`terminal_bridge.py`) emits `__MSG__{json}__END__` delimited messages; the TS side (`useBridge.ts`) parses and dispatches them.

### Key Component Flow
```
CLI (cli.py) → Bridge/UIManager → Agent → ToolManager → Individual Tools
                    ↕ (JSON messages)
              React/Ink UI (TypeScript)
```

## Development Setup

```bash
# Install Python package (editable)
pip install -e .  # or: uv pip install -e .

# Install UI dependencies
cd terminal_ui && npm install && cd ..

# Run with React UI (default)
hakken

# Run Python-only mode (no UI)
hakken --ui terminal
```

## Code Patterns

### Adding a New Tool
1. Create class in `src/hakken/tools/<category>/<name>.py`
2. Inherit from `BaseTool` (see `tools/base.py`)
3. Implement required methods:
   - `get_tool_name()` → static, returns unique tool identifier
   - `json_schema()` → OpenAI function-calling schema format
   - `act(**kwargs)` → async, executes tool logic
4. Register in `ToolManager._register_default_tools()` (`tools/manager.py`)

Example pattern from `filesystem/edit.py`:
```python
class MyTool(BaseTool):
    @staticmethod
    def get_tool_name():
        return "my_tool"
    
    async def act(self, required_param, optional_param=None):
        # Validate inputs first
        if not required_param:
            return "Error: required_param is required"
        # Execute and return result dict or error string
```

### Factory Pattern
Use `AgentFactory` (`core/factory.py`) for component creation. Never instantiate `Agent` directly:
```python
from hakken.core.factory import AgentFactory
agent = AgentFactory.create_agent(ui_manager=ui)
```

### Message Format
Messages use OpenAI's multi-content format with `cache_control` for prompt caching:
```python
{"role": "user", "content": [{"type": "text", "text": "..."}]}
```

### Tool Approval System
Tools requiring user consent set `need_user_approve=true` in args. See `system_rules.py` for approval guidelines (git push, file delete, sudo commands, etc.).

## Project Conventions

- **No comments in code** unless explicitly requested
- Use absolute file paths in all tool operations
- Tools return either `{"result": ...}` dict or `"Error: ..."` string
- Python async throughout agent layer (`async def act()`)
- Pydantic for config/settings (`core/config.py`)

## Testing

```bash
pytest tests/                    # Run all tests
pytest tests/unit/              # Unit tests only
pytest tests/integration/       # Integration tests
pytest --cov=hakken tests/      # With coverage
```

Tests use standard pytest fixtures in `conftest.py`.

## Key Files to Understand

| File | Purpose |
|------|---------|
| `core/agent.py` | Main agent loop, recursive message handling, tool execution |
| `terminal_bridge.py` | Bridge class for UI communication, UIManager abstraction |
| `tools/manager.py` | Tool registration and execution pipeline |
| `prompts/system_rules.py` | Agent behavior rules, approval guidelines |
| `history/manager.py` | Context compression, token management, trace logging |
| `terminal_ui/src/hooks/useBridge.ts` | TS-side message handling |

## Environment Variables

- `OPENAI_API_KEY` (required): API key for LLM
- `CHROMA_PERSIST_DIRECTORY`: Vector DB path for semantic search (default: `.chroma_db`)
- `MODEL_MAX_TOKENS`: Context limit in K tokens (default: 200)
- `COMPRESS_THRESHOLD`: Context usage % triggering compression (default: 0.8)

## Project-Specific Instructions

Place a `Hakken.md` file in any repo root to provide project-specific context loaded into the system prompt automatically (see `prompts/manager.py:load_hakken_instructions`).

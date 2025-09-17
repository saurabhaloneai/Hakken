# hakken | 発見
> [!IMPORTANT]
> hakken is an ai agent which needs a lot of context to provide `good` intelligent assistance.
> 
> this is like a claude-code but `opensource` hehe and i have built this from scratch.
 

![img](assets/images/interface.png)

## agent capabilities

> `chat` — conversation with automatic message compression and context awareness
>
> `planning` — mandatory todo creation for complex tasks (4+ steps) with persistent todo.md tracking
> 
> `streaming` — real-time response streaming with ESC-key interrupts for mid-conversation redirection
>
> `tools` — comprehensive toolkit: terminal commands, file operations, project search, git workflows, web search, task memory, and specialized sub-agent delegation
>
> `context` — smart context cropping with user approval, intelligent prompt management, and environment-aware reminders
>
> `memory` — persistent task memory across sessions with similarity search and context recall
>
> `tokens` — token budgeting with context window optimization and output caps
>
> `status` — real-time cost tracking, context usage monitoring, and session statistics


## data flow 

```mermaid
sequenceDiagram
    autonumber
    participant UI as hakken ui
    participant AG as conversation_agent
    participant HI as history_manager
    participant PM as prompt_manager
    participant AC as api_client (openai)
    participant TR as tool_registry/tools

    UI->>AG: user input
    AG->>HI: add user message
    AG->>HI: auto compress if needed
    AG->>TR: get tool schemas (deterministic)
    AG->>AC: chat.completions.create(..., tool_choice=auto, stream=true)
    AC-->>AG: content deltas (stream)
    AG-->>UI: stream chunks
    AC-->>AG: final assistant message (+ optional tool_calls)
    AG->>HI: add assistant message
    alt has tool_calls
      loop each tool_call
        opt approval required
          AG->>UI: approval panel [yes/no/always]
          UI-->>AG: decision (remember "always")
        end
        AG->>TR: run_tool(name, args)
        TR-->>AG: tool result (may include file paths)
        opt last tool in batch
          AG->>PM: get reminder (todos+memory+env)
        end
        AG->>HI: add role=tool message (+ reminder on last)
      end
      AG->>AC: call llm again with updated messages
    else no tool_calls
      AG-->>UI: display status (context %, cost)
      opt narrated action but no tools
        AG->>HI: inject nudge (e.g., use read_file ...)
        AG->>AC: call llm again
      end
    end
```

> [!NOTE]
> the current implmenation have some extra code which is not required if you are using good model lile sonnet-4
> 

## installation

### Option 1: Global Install (Use from anywhere)
Install globally with uv:

```bash
git clone https://github.com/saurabhaloneai/hakken.git
cd hakken
uv tool install -e .
```

### Option 2: Local Development
Install dependencies only (run from project directory):

```bash
git clone https://github.com/saurabhaloneai/hakken.git
cd hakken
uv sync
```

## setup

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Configure your API settings** by editing `.env`:

   **Using OpenRouter (Recommended - Free models available)**
   ```bash
   # Get a free API key from https://openrouter.ai/
   OPENROUTER_API_KEY=your-openrouter-api-key-here
   OPENAI_BASE_URL=https://openrouter.ai/api/v1
   OPENAI_MODEL=z-ai/glm-4.5-air:free
   ```

## usage

### If you installed with Option 1 (Global Install):
Run hakken from anywhere:

```bash
hakken
```

**Note:** You'll need to copy the `.env` file to your project directory or set environment variables globally.

### if you installed with Option 2 (Local Development):
run hakken from the project directory:

```bash
uv run hakken
```

the agent will start an interactive conversation where you can ask questions and get contextual assistance.

**Important:** Make sure your `.env` file is properly configured before running hakken!



## todo 

- [in process] add tutorials 
- [ ] improve the ui 

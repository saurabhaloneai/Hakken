# Building Hakken: A Component-Wise AI Coding Agent
*What happens when you get tired of switching between Claude, terminal, and your editor?*

## Intro

The paper "Attention is All You Need"[1] changed everything, but honestly? Most AI coding assistants still feel like glorified autocomplete. You ask a question, get an answer, then manually copy-paste commands and fix the inevitable "oops I can't see your file structure" moments. It's 2024 and we're still doing the digital equivalent of passing notes in class.

So I built Hakken - a coding agent that actually *does* things instead of just suggesting them. It streams responses in real-time, executes tools, manages todos, and handles interrupts. Think of it as Claude meets your terminal, with a healthy dose of "why doesn't this exist already?"

By the end of this post, you'll understand how to build your own component-wise agent that doesn't just chat, but actually ships code. We'll dive into streaming architectures, tool execution patterns, and the surprisingly tricky art of making an AI that can be interrupted mid-thought.

## The Problem (Or: Why I Got Annoyed)

Picture this: you're debugging a complex codebase. You ask Claude "what's wrong with my authentication flow?" It gives you a beautiful explanation but then says "I can't see your actual code." So you copy-paste seventeen files. It suggests changes. You manually apply them. Something breaks. Repeat.

Meanwhile, your terminal is open in another window, your editor in a third, and you're playing the world's most tedious game of digital telephone.

The core insight? **Modern AI coding assistants are read-only when they should be read-write.**

Jason Wei once wrote about giving language models "time to think"[2] - but what about giving them time to *act*? What if your AI could:

- Actually read your files (with line numbers!)
- Execute git commands and see the real output
- Edit code and run tests
- Stream responses while thinking, letting you interrupt with new instructions
- Keep track of todos and actually follow through on them

That's Hakken. But let's talk about how you build something like this without losing your sanity.

## The Architecture (Or: How to Make an AI That Actually Does Things)

### The Core Loop

Every AI agent needs a loop. Hakken's is beautifully simple:

```
1. User says something
2. Agent thinks (streams response)
3. Agent calls tools if needed
4. Tools execute and return data
5. Agent sees tool results, thinks more
6. Repeat until no more tools needed
7. Wait for next user input
```

But the devil is in the implementation. Let's break it down:

### Streaming + Function Calling: The Unholy Union

Here's where things get spicy. OpenAI's streaming API can return both text content *and* function calls in the same response. Most people handle these separately, but that's wrong. You want to:

```python
async for chunk in stream:
    if chunk.choices[0].delta.content:
        # Stream text to user immediately
        print(chunk.choices[0].delta.content, end="", flush=True)
    
    if chunk.choices[0].delta.tool_calls:
        # Accumulate tool calls
        self._handle_tool_call_delta(chunk)
```

The key insight: **stream the thinking, batch the doing**. Users see thoughts in real-time, but tools execute atomically.

### Tool Registry: The Plugin Architecture

Instead of hardcoding tools, I built a registry system:

```python
class ToolInterface(ABC):
    @abstractmethod
    async def act(self, **kwargs) -> Any:
        pass
    
    @abstractmethod 
    def json_schema(self) -> Dict:
        pass

class ToolRegistry:
    def register_tool(self, tool: ToolInterface):
        self.tools[tool.get_tool_name()] = tool
```

Each tool is self-contained with its own schema. Want to add file editing? Write a tool. Need git integration? Write a tool. The agent doesn't care - it just calls `registry.run_tool(name, **args)`.

This is basically the plugin architecture that VSCode uses, but for AI agents.

### The Recursion Problem

Here's where it gets mathematically interesting. When an agent calls tools, you need to:

1. Execute the tool
2. Add the result to conversation history  
3. Call the LLM again with the updated history
4. Handle any new tool calls
5. Repeat until convergence

This is essentially a fixed-point iteration:

```
f(messages) → (new_messages, tool_calls)
```

Where convergence means `tool_calls = []`.

But there's a catch: **what if it never converges?** You need circuit breakers, token limits, and graceful degradation. The math is simple; the engineering is not.

### Interrupts: The Real-Time Challenge

The hardest part isn't making an AI that thinks - it's making one that can be interrupted while thinking. Users want to inject instructions mid-stream: "actually, use TypeScript instead" or "wait, check the tests first."

I solved this with a background thread + queue pattern:

```python
# Background thread reads stdin
def _interrupt_reader():
    while not stop_event.is_set():
        line = sys.stdin.readline()
        if line.strip():
            interrupt_queue.put(line.strip())

# Main loop polls for interrupts
for chunk in stream:
    interrupt = self._poll_interrupt()
    if interrupt:
        # Inject as new user message
        self.add_message({
            "role": "user", 
            "content": f"[INTERRUPT] {interrupt}"
        })
        break
```

The beautiful part? The agent just sees it as another user message. No special handling needed.

## The Tools (Or: How to Give an AI Hands)

### File Operations: The Foundation

Every coding agent needs to read and write files. But here's the trick: **always show line numbers**.

```python
def read_file(self, path: str, start_line=None, end_line=None):
    with open(path) as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines[start_line:end_line], start_line or 1):
        yield f"{i:6d}|{line.rstrip()}"
```

Why line numbers? Because when the AI says "change line 47," you want that to mean something precise.

### Command Execution: The Power Tool

Running shell commands is where things get dangerous. You need:

1. **Timeouts** - no infinite loops
2. **Approval flows** - dangerous commands need human OK  
3. **Output capture** - both stdout and stderr
4. **Working directory tracking** - commands should compose

```python
async def run_command(self, cmd: str, timeout=30, needs_approval=True):
    if needs_approval and self._is_dangerous(cmd):
        if not await self.ui.confirm_action(f"Run: {cmd}"):
            return "Command cancelled by user"
    
    result = subprocess.run(
        cmd, shell=True, capture_output=True, 
        text=True, timeout=timeout
    )
    return result.stdout if result.returncode == 0 else result.stderr
```

### Todo Management: The Meta-Tool

Here's where it gets recursive in a beautiful way. The AI can manage its own todos:

```python
class TodoWriter(ToolInterface):
    def __init__(self):
        self.todos = []
    
    async def act(self, todos: List[Dict]):
        self.todos = todos
        self.ui.display_todos(todos)  # Show user immediately
        return f"Updated {len(todos)} todos"
    
    def get_status(self) -> str:
        return json.dumps({"todos": self.todos})
```

The magic happens in the prompt system. After every tool execution, I inject a reminder that includes current todo status. The AI sees its own progress and can update accordingly.

It's like giving the AI a notepad that it can actually read and write.

## The Prompt Engineering (Or: How to Talk to Your Agent)

### System Prompt: The Constitution

Your system prompt is basically the constitution of your agent. Mine includes:

1. **Identity**: "You are Hakken CLI, a component-wise AI agent"
2. **Capabilities**: List of available tools
3. **Behavior rules**: When to use todos, how to handle complex tasks  
4. **Context awareness**: Current directory, git status, environment

But here's the key insight: **make it dynamic**. I inject live environment info:

```python
def get_system_prompt(self):
    env_info = self.collect_environment()
    tool_schemas = self.registry.get_schemas()
    
    return f"""
You are Hakken CLI. Available tools: {tool_schemas}
Current directory: {env_info.cwd}
Git repo: {env_info.git_status}
Today: {env_info.date}

Rules:
- For complex tasks (4+ steps), create todos first
- Use tools immediately, don't just suggest
- Stream thinking, batch actions
...
"""
```

### The Reminder System

After every tool execution, I append a reminder with current state:

```
<reminder>
## Current Todo Status
- [x] Read configuration files
- [ ] Update database schema  
- [ ] Run migrations

Remember to update todos using todo_write.
</reminder>
```

This keeps the AI anchored to its current progress. Without this, it forgets what it was doing.

## The Streaming Architecture (Or: How to Think Fast and Move Things)

### The Pipeline

Streaming isn't just about speed - it's about user experience. Nobody wants to stare at a loading spinner for 30 seconds. But streaming with function calling is tricky:

```
User Input → LLM Request → Stream Processing → Tool Execution → Repeat
     ↓
[Message History] ← Tool Results ← Function Calls ← Content Chunks
```

The challenge: you're building the response while streaming it. Tool calls can come in fragments across multiple chunks.

### Handling Partial Function Calls

OpenAI streams function calls as deltas. You might get:

```json
// Chunk 1
{"function": {"name": "read_file"}}

// Chunk 2  
{"function": {"arguments": "{\"path\": \"/Users"}}

// Chunk 3
{"function": {"arguments": "/saurabh/file.py\"}"}}
```

You need to accumulate these into complete calls:

```python
def handle_tool_delta(self, delta):
    if delta.function.name:
        self.current_call['name'] = delta.function.name
    if delta.function.arguments:
        self.current_call['arguments'] += delta.function.arguments
```

Only execute when you have complete JSON.

### Error Recovery

Streaming means partial states. What if the connection drops mid-stream? What if tool execution fails?

I handle this with graceful degradation:

```python
try:
    for chunk in stream:
        # Process chunk
        pass
except Exception as e:
    # Fall back to non-streaming
    response = self.client.get_completion(request)
    self.display_message(response.content)
```

Always have a fallback.

## The Context Management (Or: How to Remember Everything Without Going Broke)

### The Token Budget Problem

Context windows are expensive. GPT-4 tokens cost real money, and users have real conversations that grow real long. You need compression strategies:

1. **Auto-compression**: When context hits 80% of limit, compress older messages
2. **Smart cropping**: Remove messages but preserve system prompt and recent context  
3. **Tool result summarization**: Don't keep every `ls` output forever

### Message Compression

I use a two-phase strategy:

```python
def compress_context(self):
    messages = self.history.get_messages()
    
    # Phase 1: Remove old tool results (keep recent)
    compressed = self.remove_old_tool_results(messages)
    
    # Phase 2: If still too long, crop from middle
    if self.estimate_tokens(compressed) > self.limit:
        compressed = self.crop_middle_messages(compressed)
    
    return compressed
```

The key insight: **preserve the edges, compress the middle**. System prompt and recent messages are sacred. Everything else is fair game.

## The Real-World Problems (Or: What Actually Goes Wrong)

### Race Conditions

Streaming + interrupts + tool execution = race conditions everywhere. Users can interrupt while tools are running. Tools can fail. Network can drop.

I solved this with state machines and careful locking:

```python
class AgentState(Enum):
    IDLE = "idle"
    THINKING = "thinking" 
    EXECUTING_TOOLS = "executing"
    INTERRUPTED = "interrupted"

async def handle_interrupt(self, text):
    if self.state == AgentState.EXECUTING_TOOLS:
        # Queue interrupt for after tools complete
        self.pending_interrupts.append(text)
    else:
        # Handle immediately
        await self.process_interrupt(text)
```

### Tool Failures

Tools fail. Files don't exist. Commands error out. Network requests timeout. Your agent needs to handle this gracefully:

```python
try:
    result = await tool.execute(**args)
except Exception as e:
    result = f"Tool failed: {str(e)}"
    # But keep going! Don't crash the whole agent
```

Failure is just another kind of data.

### The Infinite Loop Problem

What if your agent gets stuck in a loop? Calling the same failing tool over and over? You need circuit breakers:

```python
def should_execute_tool(self, tool_name, args):
    # Don't retry the same failing tool too many times
    recent_failures = self.get_recent_failures(tool_name, args)
    if len(recent_failures) > 3:
        return False, "Tool failing repeatedly"
    return True, None
```

## Performance Optimizations (Or: How to Make It Actually Fast)

### Parallel Tool Execution

Some tools can run in parallel. If the AI wants to read three files, don't do it sequentially:

```python
async def execute_tools(self, tool_calls):
    # Group by dependencies
    parallel_groups = self.group_parallel_tools(tool_calls)
    
    for group in parallel_groups:
        # Execute group in parallel
        results = await asyncio.gather(*[
            self.execute_tool(call) for call in group
        ])
```

### Caching

Cache everything that makes sense:

- File contents (with modification time checks)
- Git status (until next git operation)  
- Directory listings
- Tool schemas (static)

### Streaming Optimizations

Buffer small chunks, stream larger ones:

```python
def stream_content(self, chunk):
    self.buffer += chunk
    if len(self.buffer) > 50 or chunk.endswith('\n'):
        print(self.buffer, end='', flush=True)
        self.buffer = ''
```

This reduces flicker while maintaining responsiveness.

## The UI/UX (Or: How to Make Terminal Apps Not Suck)

### Rich Terminal Interface

Nobody wants to use a boring terminal app. I use Rich for:

- Colored output with semantic meaning
- Spinners during long operations
- Tables for structured data (file listings, todos)
- Panels for important information

```python
from rich.console import Console
from rich.panel import Panel

console = Console()
console.print(Panel("✨ Welcome to Hakken!", style="bold cyan"))
```

### Real-Time Todo Display

When the AI updates todos, show them immediately in a beautiful format:

```
✦ Project Tasks
  ✓  Read configuration files
  ◉  Update database schema
  ○  Run migrations
```

### Interrupt Handling UX

Make interrupts feel natural:

```
🤖 I'll now update the database schema...
> /stop                           # User types this
🛑 Interrupted. What would you like to change?
> actually use PostgreSQL instead
🤖 Got it, switching to PostgreSQL...
```

## Lessons Learned (Or: What I Wish Someone Had Told Me)

### 1. Start Simple, Add Complexity Gradually

I initially tried to build everything at once. Bad idea. Start with:

1. Basic chat loop
2. One simple tool (like file reading)
3. Add streaming
4. Add more tools
5. Add interrupts
6. Add todos
7. Polish UX

### 2. Function Calling is Weird

OpenAI's function calling API has quirks:

- Tool calls can be partial across chunks
- Arguments come as JSON strings (that you need to parse)
- Error handling is your problem
- The schema format is verbose and finicky

Plan for this.

### 3. Users Will Break Everything

Users will:

- Interrupt at weird times
- Feed you malformed inputs  
- Run your agent in directories without permissions
- Expect it to work with every possible shell/OS combination

Build defensively.

### 4. Context Management is Everything

Token costs add up fast. A single conversation can easily hit thousands of tokens. Your agent needs to be smart about:

- What to remember
- What to forget
- When to compress
- How to summarize

### 5. Tools Are Your Product

The quality of your agent is determined by the quality of your tools. Spend time making them:

- Robust (handle errors gracefully)
- Fast (nobody wants to wait)
- Useful (solve real problems)
- Composable (work well together)

## The Future (Or: What Comes Next)

This is just the beginning. Some ideas for where this could go:

### Multi-Agent Workflows

Instead of one monolithic agent, imagine a team:

- **Planner Agent**: Breaks down complex tasks
- **Researcher Agent**: Explores codebases and finds information  
- **Implementer Agent**: Actually writes and edits code
- **Tester Agent**: Runs tests and validates changes

### Visual Interfaces

Terminal UIs are great for developers, but what about drag-and-drop todo management? Real-time code diff views? Integration with VSCode?

### Learning from Usage

What if your agent learned from your patterns? If you always run tests after editing code, it should learn to suggest that.

### Code Understanding

Current agents are glorified text processors. The future is agents that understand:

- Code structure and dependencies
- Test coverage and quality metrics
- Performance implications of changes
- Security vulnerabilities

## Conclusion

Building Hakken taught me that the best AI tools don't just think - they act. The future of coding assistants isn't bigger language models; it's better integration between AI and the tools developers actually use.

The code is open source[3]. The ideas are freely available. The question isn't whether someone will build better coding agents - it's whether you'll be the one to do it.

Now stop reading blogs and go build something.

---

[1] https://arxiv.org/abs/1706.03762  
[2] https://www.jasonwei.net/blog/some-intuitions-about-large-language-models  
[3] https://github.com/saurabhaloneai/hakken

*"The best way to predict the future is to build it." - Alan Kay*

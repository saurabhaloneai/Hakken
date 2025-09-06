# Building Hakken: A Component-Wise AI Agent From Scratch
*What happens when you get obsessed with understanding how AI agents actually work under the hood?*

## Intro

I'll be honest - I didn't build Hakken because the world needed another coding assistant. I built it because I was fucking tired of treating AI agents like black boxes. Everyone talks about "agentic AI" and "tool use" but nobody shows you the actual gnarly implementation details. How does streaming + function calling actually work? What happens when users interrupt mid-thought? How do you make an AI that remembers its todos and actually follows through?

So I said fuck it, let's build one from scratch and document every painful detail.

In this post, we'll implement a complete AI coding agent in pure Python - streaming responses, tool execution, todo management, real-time interrupts, and all the other good stuff. Why Python? Because I think it has good aesthetics. Also Python looks like pseudocode but it has some cool features like asyncio, rich terminals, and a metric ton of libraries which makes your agent go brr brr.

This is one of the first posts that strongly focuses on the soul of actually understanding what's happening under the hood, which makes it more cool.

**Note:**
- This post assumes familiarity with Python and basic understanding of LLMs/function calling
- This implementation is for educational purposes - it covers all components but might not be production-ready
- If you don't wanna read this amazing blog post then you can check out all the code at [this repository](https://github.com/saurabhaloneai/hakken)

**AI Agent Architecture Overview:**
At its core, Hakken is a recursive message processing system that generates responses one token at a time, executes tools when needed, and maintains conversation state - like having a conversation with a really smart terminal that can actually do shit.

So let's fucking go!! We're doing it, get your coffee!! First, we'll begin with understanding what an AI agent actually is.

## What Even Is An AI Agent?

Before we dive into implementation, let's get philosophical for a hot minute. What separates a chatbot from an "agent"? 

A chatbot is like that friend who gives great advice but never actually helps you move. An agent is the friend who shows up with a truck.

The difference is **agency** - the ability to:
1. **Perceive** the environment (read files, check git status)
2. **Decide** what actions to take (should I run tests? edit this file?)
3. **Act** on those decisions (actually execute the damn commands)
4. **Learn** from the results (oh shit, that broke something)

Most "AI assistants" stop at step 2. They'll tell you what to do, but you're stuck being their hands and feet. Fuck that.

## The Architecture Deep Dive

Here's the thing nobody tells you about building AI agents: it's not about the AI part, it's about the **message passing architecture**.

At its core, every AI agent is just a fancy message queue processor:

```
[User Input] → [LLM Processing] → [Tool Calls] → [Tool Results] → [LLM Processing] → [Response]
                     ↑                                                    ↓
                     └─────────────── Recursive Loop ─────────────────────┘
```

But the devil is in the implementation. Let's break down each component and see how it actually works.

## Message History: The Memory System

First things first - your agent needs memory. Not just "remember what the user said" but "remember what I did, what worked, what failed, and what I'm supposed to do next."

In pure Python, we represent this as a simple message list:

```python
messages = [
    {"role": "system", "content": "You are Hakken, an AI coding agent..."},
    {"role": "user", "content": "Help me debug this authentication issue"},
    {"role": "assistant", "content": "I'll help you debug that. Let me first read your code.", "tool_calls": [...]},
    {"role": "tool", "tool_call_id": "123", "name": "read_file", "content": "file contents..."},
    {"role": "assistant", "content": "I see the issue. The JWT validation is missing..."}
]
```

This is literally how every modern LLM API works. The trick is in **managing this list efficiently**:

```python
class ConversationHistoryManager:
    def __init__(self):
        self.messages = []
        self.token_count = 0
    
    def add_message(self, message):
        self.messages.append(message)
        self.token_count += self._estimate_tokens(message)
        
        # Auto-compress if we're getting too long
        if self.token_count > self.max_tokens * 0.8:
            self._compress_old_messages()
    
    def _compress_old_messages(self):
        # Keep system prompt + recent messages, compress the middle
        # This is where the magic happens - smart context management
        pass
```

The key insight: **treat context window like RAM**. You have a limited budget, spend it wisely.

## Streaming: Making It Feel Alive

Nobody wants to stare at a loading spinner for 30 seconds while the AI "thinks." Streaming makes your agent feel responsive and alive. But streaming + function calling? That's where shit gets weird.

Here's the problem: OpenAI's streaming API can return both text content AND function calls in the same response. The text comes in chunks, but function calls come in fragments across multiple chunks. You might get:

```json
// Chunk 1
{"delta": {"content": "I'll help you debug that. Let me "}}

// Chunk 2  
{"delta": {"content": "read your configuration file first."}}

// Chunk 3
{"delta": {"tool_calls": [{"index": 0, "function": {"name": "read_file"}}]}}

// Chunk 4
{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "{\"path\": \"/etc"}}]}}

// Chunk 5
{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "/config.json\"}"}}]}}
```

Most people fuck this up by trying to handle them separately. The right way:

```python
class StreamProcessor:
    def __init__(self):
        self.content_buffer = ""
        self.tool_calls = []
        
    async def process_stream(self, stream):
        for chunk in stream:
            # Handle text content - stream immediately
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                self.content_buffer += content
            
            # Handle tool calls - accumulate fragments
            if chunk.choices[0].delta.tool_calls:
                self._accumulate_tool_calls(chunk.choices[0].delta.tool_calls)
        
        # Return complete message when stream ends
        return {
            "content": self.content_buffer,
            "tool_calls": self.tool_calls if self.tool_calls else None
        }
```

The key insight: **stream the thinking, batch the doing**. Users see thoughts in real-time, but tools execute atomically when the stream completes.

## Tool System: Where The Magic Happens

This is where your agent gets its superpowers. Tools are what separate a chatbot from an actual agent. But here's the thing - most people overcomplicate this shit.

A tool is just a function with a schema. That's it. Here's the interface:

```python
class ToolInterface(ABC):
    @staticmethod
    @abstractmethod
    def get_tool_name() -> str:
        pass
    
    @abstractmethod
    async def act(self, **kwargs) -> Any:
        pass
    
    @abstractmethod
    def json_schema(self) -> Dict:
        pass
```

Let's build a simple file reader tool:

```python
class FileReader(ToolInterface):
    @staticmethod
    def get_tool_name() -> str:
        return "read_file"
    
    async def act(self, file_path: str, start_line=None, end_line=None):
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            # Apply line range if specified
            if start_line or end_line:
                start_idx = (start_line - 1) if start_line else 0
                end_idx = end_line if end_line else len(lines)
                lines = lines[start_idx:end_idx]
            
            # Format with line numbers (crucial for AI)
            formatted_lines = []
            for i, line in enumerate(lines, start_line or 1):
                formatted_lines.append(f"{i:6d}|{line.rstrip()}")
            
            return {
                "content": '\n'.join(formatted_lines),
                "file_path": file_path,
                "total_lines": len(lines)
            }
        except Exception as e:
            return {"error": f"Error reading file: {str(e)}"}
    
    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read file contents with optional line range",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to file"},
                        "start_line": {"type": "integer", "description": "Starting line"},
                        "end_line": {"type": "integer", "description": "Ending line"}
                    },
                    "required": ["file_path"]
                }
            }
        }
```

The registry is dead simple:

```python
class ToolRegistry:
    def __init__(self):
        self.tools = {}
    
    def register_tool(self, tool: ToolInterface):
        self.tools[tool.get_tool_name()] = tool
    
    async def run_tool(self, tool_name: str, **kwargs):
        tool = self.tools.get(tool_name)
        if not tool:
            return {"error": f"Tool {tool_name} not found"}
        return await tool.act(**kwargs)
    
    def get_schemas(self):
        return [tool.json_schema() for tool in self.tools.values()]
```

This is basically the plugin architecture that VSCode uses, but for AI agents. Want to add git support? Write a tool. Need to run shell commands? Write a tool. The agent doesn't give a fuck about implementation details.

## The Recursive Loop: Where Shit Gets Real

Here's where building AI agents becomes actually interesting. It's not just "call LLM, get response, done." It's a recursive process that can theoretically run forever.

The loop looks like this:

```python
async def _recursive_message_handling(self):
    while True:
        # 1. Get LLM response (might include tool calls)
        response = await self.call_llm(self.messages)
        
        # 2. Add response to history
        self.messages.append(response)
        
        # 3. If no tool calls, we're done
        if not response.tool_calls:
            break
            
        # 4. Execute tools and add results to history
        for tool_call in response.tool_calls:
            result = await self.execute_tool(tool_call)
            self.messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })
        
        # 5. Loop back - LLM will see tool results and continue
```

This is essentially a fixed-point iteration: `f(messages) → (new_messages, tool_calls)` where convergence means `tool_calls = []`.

But here's the scary part: **what if it never converges?** What if your agent gets stuck in a loop, calling the same failing tool over and over? You need circuit breakers:

```python
class CircuitBreaker:
    def __init__(self, max_iterations=10, max_same_tool_failures=3):
        self.max_iterations = max_iterations
        self.max_same_tool_failures = max_same_tool_failures
        self.tool_failure_counts = {}
        self.iteration_count = 0
    
    def should_continue(self, tool_name=None, failed=False):
        self.iteration_count += 1
        
        if self.iteration_count > self.max_iterations:
            return False, "Max iterations reached"
        
        if failed and tool_name:
            self.tool_failure_counts[tool_name] = self.tool_failure_counts.get(tool_name, 0) + 1
            if self.tool_failure_counts[tool_name] > self.max_same_tool_failures:
                return False, f"Tool {tool_name} failing repeatedly"
        
        return True, None
```

The math is simple; the engineering is not.

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

## What I Actually Learned (The Real Shit)

Building Hakken wasn't just about creating another AI tool - it was about understanding the underlying mechanics of intelligence and agency. Here's what I actually discovered:

### 1. It's All About Message Passing

Every "intelligent" system is just sophisticated message routing. Whether it's neurons firing, microservices communicating, or an AI agent processing requests - it's all message passing at different scales. Understanding this fundamentally changed how I think about AI systems.

### 2. The Hard Part Isn't The AI

The LLM is the easy part. OpenAI already solved that problem. The hard part is:
- Managing state across recursive calls
- Handling edge cases gracefully  
- Making streaming + function calling work together
- Building robust error recovery
- Creating intuitive user experiences

### 3. Emergence Is Real But Predictable

When you combine simple components (message history + tools + recursion), complex behaviors emerge. But it's not magic - it's just composition. Once you understand the patterns, you can predict and control the emergent behavior.

### 4. Users Will Always Surprise You

No matter how robust you think your system is, users will find ways to break it. They'll interrupt at weird times, feed malformed inputs, expect impossible things. Building for the happy path is easy; building for the edge cases is engineering.

### 5. The Future Is Agentic

We're moving from "AI that answers questions" to "AI that gets shit done." The next breakthrough isn't in model capabilities - it's in building agents that can reliably execute complex workflows in messy, real-world environments.

## The Implementation Details That Matter

If you want to build your own agent, here are the non-obvious things that matter:

**Context Management**: Treat your context window like precious memory. Compress aggressively, but preserve the important bits.

**Error Recovery**: Every tool can fail. Every network call can timeout. Plan for it.

**State Management**: Keep your message history clean and your state machines simple.

**User Experience**: Streaming isn't just about speed - it's about making the AI feel alive and responsive.

**Circuit Breakers**: Infinite loops are real. Prevent them.

## What's Next?

This is just the beginning. Some ideas for where agents are heading:

- **Multi-modal agents** that can see and hear, not just read text
- **Persistent agents** that remember across sessions and learn from usage patterns  
- **Collaborative agents** that work in teams to solve complex problems
- **Embedded agents** that live inside your development environment

The fundamental architecture will stay the same: message passing + tools + recursion. But the applications will blow your mind.

## Why I'm Sharing This

I could have kept this knowledge to myself and built a startup around it. But I believe the future is better when more people understand how these systems actually work. 

The AI revolution isn't happening to us - it's happening through us. The more people who understand the underlying mechanics, the better tools we'll build and the more thoughtfully we'll integrate AI into our workflows.

Plus, I'm fucking tired of people treating AI agents like black magic. It's just code. Good code, but still just code.

## Go Build Something

The code is open source. The ideas are freely available. The question isn't whether someone will build better coding agents - it's whether you'll be the one to do it.

Stop reading blogs. Start shipping code.

---

**Links:**
- [Hakken Repository](https://github.com/saurabhaloneai/hakken)
- [OpenAI Function Calling Docs](https://platform.openai.com/docs/guides/function-calling)
- [Rich Terminal Library](https://github.com/Textualize/rich)

**Thanks for reading!**

If this helped you understand AI agents better, star the repo and build something cool with it.

*"The best way to understand a system is to build it from scratch." - Me, apparently*

# hakken 

An interactive CLI AI agent(llm in feedback-loop) that helps you with tasks through natural conversation.

>[!IMPORTANT]
>
> I build this project understand about agents work and how to build effective agents.

![img](./assets/hakken.png)

## features

- **Tool Integration** - File system operations, web search, command execution
- **Permission System** - Tool usage requires explicit approval
- **Markdown Support** - Rich text rendering with syntax highlighting
- **Human in the loop** - Agent will ask for approval to use tools and you ask stop agent if you want to stop the agent and give feedback to the agent.
- [ ] Memory 
- [ ] Long Context Management
- [ ] Evaluation 

## setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/hakken.git
cd hakken
```

2. Install Python dependencies:
```bash
uv sync
# or
pip install -e .
```

3. Install Node dependencies:
```bash
cd hakken-agent
npm install
```

4. Create `.env` file with your OpenAI API key:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

5. Build the project:
```bash
npm run build
```

## usage

Run the agent

```bash
hakken
```

### Keyboard Shortcuts

- `ESC` - Cancel pending tool approval
- `Ctrl+S` - Save conversation history
- `Ctrl+C` - Exit

## Project Structure

```
hakken/
├── hakken-agent/          # CLI Application
│   ├── src/
│   │   ├── components/    # React UI components
│   │   │   ├── types/     # TypeScript interfaces
│   │   │   └── utils/     # Helper functions
│   │   ├── hooks/         # Custom React hooks
│   │   ├── python/        # Python backend
│   │   │   ├── core/      # Agent and client logic
│   │   │   ├── prompts/   # AI prompts
│   │   │   └── tools/     # Tool definitions
│   │   ├── bridge.py      # Python-Node.js bridge
│   │   ├── ui.tsx         # Main UI entry point
│   │   ├── index.js       # CLI entry point
│   │   └── setup.js       # Setup configuration
│   ├── build.sh           # Build script
│   ├── package.json       # Node.js dependencies
│   └── tsconfig.json      # TypeScript config
├── .github/               # GitHub templates
│   ├── ISSUE_TEMPLATE/    # Issue templates
│   └── pull_request_template.md
├── pyproject.toml         # Python package metadata
├── uv.lock                # Python dependency lock
├── README.md              # This file
├── LICENSE                # MIT License
├── CONTRIBUTING.md        # Contribution guidelines
└── CHANGELOG.md           # Version history
```

The project uses a hybrid architecture:
- **Root level**: Python package metadata and configuration
- **hakken-agent/**: Complete CLI application with React UI and Python backend

## license

MIT License - see LICENSE file for details

![img](./assets/hakken-bye.png)

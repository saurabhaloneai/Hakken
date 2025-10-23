# Hakken UI Architecture

This directory contains the refactored UI components for Hakken, organized into a clean, modular structure.

## Directory Structure

```
src/
├── components/          # React components
│   ├── types/          # TypeScript type definitions
│   │   └── index.ts
│   ├── utils/          # Utility functions
│   │   ├── constants.ts
│   │   └── stringUtils.ts
│   ├── MarkdownText.tsx
│   ├── MessageItem.tsx
│   ├── CurrentResponse.tsx
│   ├── Header.tsx
│   ├── ThinkingIndicator.tsx
│   ├── LoadingIndicator.tsx
│   ├── ToolApprovalPrompt.tsx
│   ├── InputBox.tsx
│   └── index.ts        # Barrel export
├── hooks/              # Custom React hooks
│   ├── usePythonBridge.ts
│   ├── useTerminalSize.ts
│   ├── useKeyboardShortcuts.ts
│   ├── useQuoteRotation.ts
│   └── index.ts        # Barrel export
├── python/             # Python backend
├── ui.tsx             # Main application entry
└── bridge.py          # Python bridge

```

## Components

### Display Components
- **MarkdownText** - Renders markdown with syntax highlighting
- **MessageItem** - Displays individual chat messages (memoized for performance)
- **CurrentResponse** - Shows streaming agent responses
- **Header** - ASCII art header with working directory
- **ThinkingIndicator** - Animated thinking/working state
- **LoadingIndicator** - Initial loading animation

### Interactive Components
- **InputBox** - Main input field with status messages
- **ToolApprovalPrompt** - Tool permission approval UI

## Hooks

### State Management
- **usePythonBridge** - Manages Python process communication and state
  - Messages
  - Agent modes (loading, ready, thinking, approval)
  - Tool permissions
  - Status updates

### UI Utilities
- **useTerminalSize** - Tracks terminal width for responsive layout
- **useKeyboardShortcuts** - Global keyboard shortcuts (ESC, Ctrl+S, etc.)
- **useQuoteRotation** - Rotates thinking quotes every 2 seconds

## Types

All TypeScript interfaces are centralized in `components/types/`:
- `Message` - Chat message structure
- `PendingTool` - Tool approval request
- `PythonMessage` - Bridge message format
- `AppMode` - Application state machine

## Utilities

### String Utilities (`components/utils/stringUtils.ts`)
- `truncateMiddle()` - Truncate long strings with ellipsis
- `truncatePath()` - Smart path truncation for display
- `toolShortLabel()` - Convert tool names to friendly labels

### Constants (`components/utils/constants.ts`)
- `WORKING_QUOTES` - Array of thinking status messages
- `TOOL_LABELS` - Human-friendly tool names

## Performance Optimizations

All components are memoized using `React.memo()` with custom comparison functions to prevent unnecessary re-renders:

1. **MarkdownText** - Only re-renders when content changes
2. **MessageItem** - Only re-renders when message properties change
3. **CurrentResponse** - Only re-renders during streaming
4. **Header** - Only re-renders on terminal resize or directory change

This ensures that the quote rotation (every 2 seconds) only updates the thinking indicator, not the entire component tree.

## Building

```bash
npm run build
```

This compiles TypeScript and bundles all components into the `dist/` directory.


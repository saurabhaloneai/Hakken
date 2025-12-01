#!/usr/bin/env node
import React, { useState, useEffect } from 'react'
import { render, Box, Text } from 'ink'
import {
  Header,
  MessageList,
  StreamingResponse,
  Spinner,
  InputBox,
  LoadingScreen,
  TodoList,
  HakkenModal
} from './components/index.js'
import { useBridge, useTerminalWidth, useKeyboard, useHakken } from './hooks/index.js'

const Divider: React.FC<{ width: number }> = ({ width }) => {
  const length = Math.max(24, Math.min(width - 4, 80))
  return <Text dimColor color="gray">{'─'.repeat(length)}</Text>
}

const App: React.FC = () => {
  const [input, setInput] = useState('')
  const [showToolArgs, setShowToolArgs] = useState(false)

  const {
    mode,
    messages,
    currentResponse,
    workingDir,
    pendingTool,
    statusLine,
    todos,
    sendUserInput,
    sendApproval,
    stopAgent
  } = useBridge()

  const width = useTerminalWidth()
  const hakken = useHakken(workingDir)

  useKeyboard({
    mode,
    hakkenOpen: hakken.isOpen,
    onStop: stopAgent,
    onApprove: () => sendApproval(true),
    onDeny: () => sendApproval(false),
    onToggleArgs: () => setShowToolArgs(s => !s),
    onToggleHakken: hakken.toggle
  })

  useEffect(() => {
    process.stdout.write('\x1Bc')
    process.stdout.write('\x1B[?25l')
    return () => { process.stdout.write('\x1B[?25h') }
  }, [])

  const handleSubmit = () => {
    const msg = input.trim()
    if (!msg) return
    sendUserInput(msg)
    setInput('')
  }

  const queuedCount = messages.filter(m => m.queued).length

  // Extract the latest system info (context window, cost) from system messages
  const getSystemInfo = (): string => {
    const systemMessages = messages.filter(m => m.type === 'system')
    for (let i = systemMessages.length - 1; i >= 0; i--) {
      const content = systemMessages[i].content
      // Match patterns like "(context window: X%, total cost: Y$)"
      const match = content.match(/\(context window:.*?\)/)
      if (match) return match[0]
    }
    return ''
  }

  const systemInfo = getSystemInfo()

  if (mode === 'loading') {
    return <LoadingScreen />
  }

  if (hakken.isOpen) {
    return (
      <Box flexDirection="column" paddingX={2}>
        <HakkenModal
          content={hakken.content}
          isDirty={hakken.isDirty}
          filePath={hakken.filePath}
          onUpdate={hakken.update}
          onClose={hakken.close}
        />
      </Box>
    )
  }

  return (
    <Box flexDirection="column" paddingX={2}>
      {/* Header at top */}
      <Header workingDirectory={workingDir} terminalWidth={width} />

      {/* Messages */}
      <Box flexDirection="column" marginBottom={1}>
        <MessageList messages={messages} />
        <StreamingResponse content={currentResponse} />
        {(mode === 'thinking' || mode === 'executing') && !currentResponse && (
          <Spinner label={statusLine} />
        )}
      </Box>

      <Divider width={width} />

      {/* Tasks panel - positioned above input, always visible at bottom */}
      {todos.length > 0 && <TodoList items={todos} width={width} />}

      <InputBox
        mode={mode}
        value={input}
        onChange={setInput}
        onSubmit={handleSubmit}
        queuedCount={queuedCount}
        pendingTool={pendingTool}
        showToolArgs={showToolArgs}
        systemInfo={systemInfo}
      />
    </Box>
  )
}

export default App

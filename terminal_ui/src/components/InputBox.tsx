import React from 'react'
import { Box, Text } from 'ink'
import TextInput from 'ink-text-input'
import { AppMode, ToolRequest } from '../types.js'
import { ToolApproval } from './ToolApproval.js'

interface InputBoxProps {
  mode: AppMode
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  queuedCount: number
  pendingTool: ToolRequest | null
  showToolArgs: boolean
  systemInfo?: string
}

export const InputBox: React.FC<InputBoxProps> = ({
  mode,
  value,
  onChange,
  onSubmit,
  queuedCount,
  pendingTool,
  showToolArgs,
  systemInfo
}) => {
  const isBusy = mode === 'thinking' || mode === 'executing' || mode === 'responding'
  const busyLabel =
    mode === 'thinking'
      ? 'Thinking'
      : mode === 'executing'
        ? 'Executing'
        : mode === 'responding'
          ? 'Responding'
          : 'Processing'
  
  return (
    <Box flexDirection="column" marginTop={1}>
      {mode === 'approval' && pendingTool ? (
        <ToolApproval tool={pendingTool} showArgs={showToolArgs} />
      ) : (
        <Box flexDirection="column">
          <Text dimColor color="gray">prompt</Text>
          <Box 
            borderStyle="round" 
            borderColor="cyan" 
            paddingLeft={1} 
            paddingRight={1}
          >
            <Text color="cyanBright">› </Text>
            {isBusy ? (
              <Text color="greenBright">
                {busyLabel}...
                {queuedCount > 0 && <Text dimColor color="yellow"> ({queuedCount} queued)</Text>}
              </Text>
            ) : (
              <TextInput
                value={value}
                onChange={onChange}
                onSubmit={onSubmit}
                placeholder="Type message..."
              />
            )}
          </Box>
          {!isBusy && queuedCount > 0 && (
            <Text dimColor color="yellow">queue · {queuedCount}</Text>
          )}
        </Box>
      )}
      <Box justifyContent="space-between">
        <Text dimColor>
          <Text color="cyan">Esc</Text> exit  {' '}
          <Text color="cyan">Enter</Text> send  {' '}
          <Text color="cyan">Ctrl+S</Text> stop  {' '}
          <Text color="magenta">⇧Tab</Text> hakken
          {pendingTool && (
            <Text>{'  '}<Text color="cyan">A</Text> args</Text>
          )}
        </Text>
        {systemInfo && (
          <Text color="yellow">{systemInfo}</Text>
        )}
      </Box>
    </Box>
  )
}

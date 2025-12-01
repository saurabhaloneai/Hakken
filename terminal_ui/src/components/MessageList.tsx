import React from 'react'
import { Box, Text } from 'ink'
import type { TextProps } from 'ink'
import { Message } from '../types.js'
import { MessageBubble } from './MessageBubble.js'
import type { MessageBubbleVariant } from './MessageBubble.js'
import { formatToolResult, parseToolMessage, FormattedResult } from './utils/formatToolResult.js'

interface MessageListProps {
  messages: Message[]
}

const getUserMeta = (msg: Message): string | undefined => {
  const badges = []
  if (msg.queued) badges.push('queued')
  if (msg.forced) badges.push('forced')
  return badges.length ? badges.join(' · ') : undefined
}

type MessagePreset = {
  label: string
  color: TextProps['color']
  variant: MessageBubbleVariant
  icon: string
}

const MESSAGE_PRESETS: Record<Message['type'], MessagePreset> = {
  user: { label: 'You', color: 'cyanBright', variant: 'solid', icon: '●' },
  agent: { label: 'Agent', color: 'magentaBright', variant: 'solid', icon: '◆' },
  system: { label: 'System', color: 'gray', variant: 'ghost', icon: '◇' },
  error: { label: 'Error', color: 'redBright', variant: 'solid', icon: '⚠' },
  tool: { label: 'Tool', color: 'blueBright', variant: 'solid', icon: '⌘' }
}

// Render tool message with clean formatting
const ToolMessage: React.FC<{ content: string }> = ({ content }) => {
  const parsed = parseToolMessage(content)
  
  if (!parsed) {
    // Fallback for non-standard tool messages (like preparing messages)
    return (
      <Box>
        <Text color="blueBright">⌘ Tool</Text>
        <Text color="blueBright"> ❯ </Text>
        <Text>{content}</Text>
      </Box>
    )
  }
  
  const formatted = formatToolResult(parsed.toolName, parsed.result)
  const isOk = parsed.status === '[ok]' || parsed.status === 'ok' || parsed.status === '✅'
  const statusIcon = isOk ? '✅' : '❌'
  const statusColor = isOk ? 'green' : 'red'
  
  return (
    <Box flexDirection="column">
      <Box>
        <Text color="blueBright">⌘ </Text>
        <Text bold color="blueBright">{formatted.label}</Text>
        <Text color="blueBright"> ❯ </Text>
        <Text color={statusColor}>{statusIcon} </Text>
        <Text>{formatted.summary}</Text>
      </Box>
      {formatted.details && formatted.details.length > 0 && (
        <Box flexDirection="column" marginLeft={4}>
          {formatted.details.map((line, i) => (
            <Text key={i} dimColor>{line}</Text>
          ))}
        </Box>
      )}
    </Box>
  )
}

export const MessageList: React.FC<MessageListProps> = ({ messages }) => {
  // Filter out system messages - they'll be shown in the status bar instead
  const visibleMessages = messages.filter(msg => msg.type !== 'system')
  
  return (
    <Box flexDirection="column">
      {visibleMessages.map((msg, idx) => (
        <Box key={idx} marginBottom={1}>
          {msg.type === 'tool' ? (
            <ToolMessage content={msg.content} />
          ) : (
            <MessageBubble
              label={MESSAGE_PRESETS[msg.type].label}
              color={MESSAGE_PRESETS[msg.type].color}
              content={msg.content}
              meta={msg.type === 'user' ? getUserMeta(msg) : undefined}
              variant={MESSAGE_PRESETS[msg.type].variant}
              icon={MESSAGE_PRESETS[msg.type].icon}
              markdown={msg.type === 'agent'}
            />
          )}
        </Box>
      ))}
    </Box>
  )
}

import React from 'react'
import { Box, Text, TextProps } from 'ink'
import { MarkdownText } from './MarkdownText.js'

export type MessageBubbleVariant = 'solid' | 'ghost'

interface MessageBubbleProps {
  label: string
  color?: TextProps['color']
  content: string
  meta?: string
  variant?: MessageBubbleVariant
  icon?: string
  markdown?: boolean
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  label,
  color = 'gray',
  content,
  meta,
  variant = 'solid',
  icon,
  markdown = false
}) => {
  const contentColor: TextProps['color'] | undefined = variant === 'ghost' ? 'gray' : undefined
  const isMultiline = content.includes('\n')

  // For multiline markdown content, render header separately
  if (markdown && isMultiline) {
    return (
      <Box flexDirection="column">
        <Box flexDirection="row">
          <Text>
            {icon && <Text color={color}>{icon} </Text>}
            <Text bold color={color}>{label}</Text>
            <Text color={color}> ❯</Text>
            {meta && (
              <Text dimColor color={variant === 'ghost' ? 'gray' : color}> · {meta}</Text>
            )}
          </Text>
        </Box>
        <Box marginLeft={2}>
          <MarkdownText color={contentColor}>{content}</MarkdownText>
        </Box>
      </Box>
    )
  }

  // Single line or non-markdown
  return (
    <Box>
      <Box flexDirection="row">
        <Text>
          {icon && <Text color={color}>{icon} </Text>}
          <Text bold color={color}>{label}</Text>
          <Text color={color}> ❯</Text>
          {meta && (
            <Text dimColor color={variant === 'ghost' ? 'gray' : color}> · {meta}</Text>
          )}
          <Text color={contentColor}> {content}</Text>
        </Text>
      </Box>
    </Box>
  )
}

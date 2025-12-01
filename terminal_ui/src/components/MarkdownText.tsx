import React from 'react'
import { Box, Text, TextProps } from 'ink'

interface MarkdownTextProps {
  children: string
  color?: TextProps['color']
  indent?: string
  width?: number
}

interface TextSegment {
  text: string
  bold?: boolean
  italic?: boolean
  code?: boolean
  dimColor?: boolean
}

const parseInlineMarkdown = (text: string): TextSegment[] => {
  const segments: TextSegment[] = []
  let remaining = text
  
  // Simple approach: process the string character by character
  let i = 0
  let currentText = ''
  
  while (i < remaining.length) {
    let matched = false
    
    // Check for **bold**
    if (remaining.slice(i).startsWith('**')) {
      const endIdx = remaining.indexOf('**', i + 2)
      if (endIdx !== -1) {
        if (currentText) {
          segments.push({ text: currentText })
          currentText = ''
        }
        segments.push({ text: remaining.slice(i + 2, endIdx), bold: true })
        i = endIdx + 2
        matched = true
      }
    }
    
    // Check for *italic* (but not **)
    if (!matched && remaining[i] === '*' && remaining[i + 1] !== '*') {
      const endIdx = remaining.indexOf('*', i + 1)
      if (endIdx !== -1 && remaining[endIdx + 1] !== '*') {
        if (currentText) {
          segments.push({ text: currentText })
          currentText = ''
        }
        segments.push({ text: remaining.slice(i + 1, endIdx), italic: true })
        i = endIdx + 1
        matched = true
      }
    }
    
    // Check for `code`
    if (!matched && remaining[i] === '`') {
      const endIdx = remaining.indexOf('`', i + 1)
      if (endIdx !== -1) {
        if (currentText) {
          segments.push({ text: currentText })
          currentText = ''
        }
        segments.push({ text: remaining.slice(i + 1, endIdx), code: true })
        i = endIdx + 1
        matched = true
      }
    }
    
    if (!matched) {
      currentText += remaining[i]
      i++
    }
  }
  
  if (currentText) {
    segments.push({ text: currentText })
  }
  
  return segments.length ? segments : [{ text }]
}

const renderSegments = (segments: TextSegment[], baseColor?: TextProps['color']): React.ReactNode[] => {
  return segments.map((segment, idx) => {
    if (segment.code) {
      return (
        <Text key={idx} color="cyan" backgroundColor="gray">
          {` ${segment.text} `}
        </Text>
      )
    }
    
    return (
      <Text
        key={idx}
        bold={segment.bold}
        italic={segment.italic}
        dimColor={segment.dimColor}
        color={segment.bold ? 'white' : baseColor}
      >
        {segment.text}
      </Text>
    )
  })
}

export const MarkdownLine: React.FC<{ line: string; color?: TextProps['color']; indent?: string; isCode?: boolean; width?: number }> = ({ 
  line, 
  color,
  indent = '  ',
  isCode = false,
  width
}) => {
  const textWidth = width ? width - 6 : undefined
  
  // Code block content - render as-is with code styling
  if (isCode) {
    return (
      <Box width={textWidth}>
        <Text color="gray" wrap="wrap">
          {indent}  <Text color="white">{line}</Text>
        </Text>
      </Box>
    )
  }

  // Handle list items
  const listMatch = line.match(/^(\s*)([-*•])\s+(.*)$/)
  if (listMatch) {
    const [, spaces, , content] = listMatch
    const segments = parseInlineMarkdown(content)
    return (
      <Box width={textWidth}>
        <Text wrap="wrap">
          {indent}{spaces}<Text color="cyan">•</Text> {renderSegments(segments, color)}
        </Text>
      </Box>
    )
  }
  
  // Handle headers
  const headerMatch = line.match(/^(#{1,3})\s+(.*)$/)
  if (headerMatch) {
    const [, hashes, content] = headerMatch
    const level = hashes.length
    return (
      <Box width={textWidth}>
        <Text bold color={level === 1 ? 'cyanBright' : level === 2 ? 'cyan' : 'white'} wrap="wrap">
          {indent}{content}
        </Text>
      </Box>
    )
  }
  
  // Handle code blocks marker - show language hint
  if (line.trim().startsWith('```')) {
    const lang = line.trim().slice(3).trim()
    if (lang) {
      return <Text dimColor color="gray">{indent}─── {lang} ───</Text>
    }
    return <Text dimColor color="gray">{indent}───────────</Text>
  }
  
  // Regular line with inline formatting
  const segments = parseInlineMarkdown(line)
  return (
    <Box width={textWidth}>
      <Text color={color} wrap="wrap">{indent}{renderSegments(segments, color)}</Text>
    </Box>
  )
}

export const MarkdownText: React.FC<MarkdownTextProps> = ({ children, color, indent = '  ', width }) => {
  if (!children) return null
  
  const lines = children.split('\n')
  let inCodeBlock = false
  
  return (
    <Box flexDirection="column" width={width}>
      {lines.map((line, idx) => {
        // Toggle code block state
        if (line.trim().startsWith('```')) {
          const wasInCodeBlock = inCodeBlock
          inCodeBlock = !inCodeBlock
          return <MarkdownLine key={idx} line={line} color={color} indent={indent} isCode={false} width={width} />
        }
        
        return <MarkdownLine key={idx} line={line} color={color} indent={indent} isCode={inCodeBlock} width={width} />
      })}
    </Box>
  )
}

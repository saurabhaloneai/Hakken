import React, { useState, useEffect } from 'react'
import { Box, Text, useInput } from 'ink'
import TextInput from 'ink-text-input'

interface HakkenModalProps {
  content: string
  isDirty: boolean
  filePath: string
  onUpdate: (content: string) => void
  onClose: (save: boolean) => void
}

export const HakkenModal: React.FC<HakkenModalProps> = ({
  content,
  isDirty,
  filePath,
  onUpdate,
  onClose
}) => {
  const [lines, setLines] = useState<string[]>([])
  const [cursor, setCursor] = useState(0)
  const [editMode, setEditMode] = useState(false)
  const [editValue, setEditValue] = useState('')

  useEffect(() => {
    setLines(content.split('\n'))
    setCursor(0)
  }, [content])

  useInput((input, key) => {
    if (editMode) {
      if (key.return) {
        const newLines = [...lines]
        newLines[cursor] = editValue
        setLines(newLines)
        onUpdate(newLines.join('\n'))
        setEditMode(false)
      }
      if (key.escape) {
        setEditMode(false)
      }
      return
    }

    if (key.escape) {
      onClose(false)
      return
    }

    if (key.upArrow) {
      setCursor(c => Math.max(0, c - 1))
    }
    if (key.downArrow) {
      setCursor(c => Math.min(lines.length - 1, c + 1))
    }
    if (key.return) {
      setEditValue(lines[cursor] || '')
      setEditMode(true)
    }
    if (input === 's' && key.ctrl) {
      onClose(true)
    }
    if (input === 'a') {
      const newLines = [...lines, '']
      setLines(newLines)
      setCursor(newLines.length - 1)
      setEditValue('')
      setEditMode(true)
    }
    if (input === 'd' && lines.length > 1) {
      const newLines = lines.filter((_, i) => i !== cursor)
      setLines(newLines)
      onUpdate(newLines.join('\n'))
      setCursor(c => Math.min(c, newLines.length - 1))
    }
  })

  const visibleLines = 12
  const start = Math.max(0, cursor - Math.floor(visibleLines / 2))
  const visible = lines.slice(start, start + visibleLines)

  return (
    <Box flexDirection="column" borderStyle="round" borderColor="gray" paddingX={1}>
      <Box justifyContent="space-between">
        <Text bold>Hakken.md</Text>
        <Text dimColor>{isDirty ? '●' : '○'}</Text>
      </Box>

      <Box flexDirection="column" marginY={1}>
        {visible.map((line, i) => {
          const idx = start + i
          const isCurrent = idx === cursor
          return (
            <Box key={idx}>
              <Text color={isCurrent ? 'cyan' : 'gray'}>{isCurrent ? '›' : ' '} </Text>
              {editMode && isCurrent ? (
                <TextInput value={editValue} onChange={setEditValue} focus={true} />
              ) : (
                <Text color={isCurrent ? 'white' : 'gray'}>{line || ' '}</Text>
              )}
            </Box>
          )
        })}
      </Box>

      <Text dimColor>
        <Text color="cyan">↑↓</Text> nav  
        <Text color="cyan"> Enter</Text> edit  
        <Text color="cyan"> a</Text> add  
        <Text color="cyan"> d</Text> del  
        <Text color="cyan"> ^S</Text> save  
        <Text color="cyan"> Esc</Text> close
      </Text>
    </Box>
  )
}

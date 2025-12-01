import React from 'react'
import { Box, Text } from 'ink'
import { ToolRequest } from '../types.js'

interface ToolApprovalProps {
  tool: ToolRequest
  showArgs: boolean
}

const truncate = (s: string, max: number): string => {
  if (s.length <= max) return s
  return s.slice(0, max - 3) + '...'
}

const formatArgLines = (args: string): string[] => {
  if (!args) return ['(no arguments)']
  return args.split('\n').map(line => line || ' ')
}

const ActionButton: React.FC<{ hotkey: string; label: string; color?: string }> = ({ 
  hotkey, 
  label, 
  color = 'gray' 
}) => (
  <Box marginRight={2}>
    <Text color={color}>[</Text>
    <Text bold color="white">{hotkey}</Text>
    <Text color={color}>]</Text>
    <Text color={color}> {label}</Text>
  </Box>
)

export const ToolApproval: React.FC<ToolApprovalProps> = ({ tool, showArgs }) => {
  const argLines = formatArgLines(tool.args)
  const preview = truncate(tool.args || '', 100) || '(no arguments)'
  
  return (
    <Box 
      flexDirection="column" 
      borderStyle="round" 
      borderColor="yellow"
      paddingX={2}
      paddingY={1}
      marginY={1}
    >
      {/* Header */}
      <Box marginBottom={1}>
        <Text color="yellow">◆ </Text>
        <Text bold color="yellow">Approve Tool</Text>
        <Text color="gray"> │ </Text>
        <Text color="cyan">{tool.name}</Text>
      </Box>
      
      {/* Arguments Section */}
      <Box 
        flexDirection="column" 
        borderStyle="single" 
        borderColor="gray"
        paddingX={1}
        paddingY={0}
      >
        <Box marginBottom={showArgs ? 1 : 0}>
          <Text dimColor>{showArgs ? '▼ Arguments' : '▶ Arguments'}</Text>
        </Box>
        
        {showArgs ? (
          <Box flexDirection="column">
            {argLines.map((line, idx) => (
              <Text key={idx} color="white">{line}</Text>
            ))}
          </Box>
        ) : (
          <Text dimColor>{preview}</Text>
        )}
      </Box>
      
      {/* Actions */}
      <Box marginTop={1} justifyContent="flex-start">
        <ActionButton hotkey="y" label="approve" color="green" />
        <ActionButton hotkey="n" label="deny" color="red" />
        <ActionButton hotkey="a" label="details" color="blue" />
      </Box>
    </Box>
  )
}

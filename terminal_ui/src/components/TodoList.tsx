import React from 'react'
import { Box, Text } from 'ink'

export interface TodoItem {
  id: string
  content: string
  status: 'pending' | 'in_progress' | 'completed'
}

interface TodoListProps {
  items: TodoItem[]
  width?: number
}

const StatusIcon: React.FC<{ status: TodoItem['status'] }> = ({ status }) => {
  switch (status) {
    case 'completed':
      return <Text color="green">[x]</Text>
    case 'in_progress':
      return <Text color="cyan">[~]</Text>
    case 'pending':
      return <Text dimColor>[ ]</Text>
  }
}

const TodoRow: React.FC<{ item: TodoItem; maxWidth: number }> = ({ item, maxWidth }) => {
  const isCompleted = item.status === 'completed'
  const isInProgress = item.status === 'in_progress'
  
  // Truncate content if too long
  const contentMaxWidth = maxWidth - 5 // Account for icon and spacing
  const displayContent = item.content.length > contentMaxWidth 
    ? item.content.slice(0, contentMaxWidth - 3) + '...'
    : item.content
  
  return (
    <Box>
      <Box width={4}>
        <StatusIcon status={item.status} />
      </Box>
      <Text
        color={isInProgress ? 'cyan' : isCompleted ? 'greenBright' : 'white'}
        dimColor={isCompleted}
        strikethrough={isCompleted}
      >
        {displayContent}
      </Text>
    </Box>
  )
}

export const TodoList: React.FC<TodoListProps> = ({ items, width = 60 }) => {
  if (!items || items.length === 0) return null
  
  // Group items by status
  const inProgress = items.filter(i => i.status === 'in_progress')
  const pending = items.filter(i => i.status === 'pending')
  const completed = items.filter(i => i.status === 'completed')
  
  // Calculate stats
  const total = items.length
  const completedCount = completed.length
  const progress = Math.round((completedCount / total) * 100)
  
  // Create progress bar
  const barWidth = Math.min(20, width - 20)
  const filledWidth = Math.round((completedCount / total) * barWidth)
  const emptyWidth = barWidth - filledWidth
  const progressBar = '#'.repeat(filledWidth) + '-'.repeat(emptyWidth)
  
  const maxContentWidth = Math.min(width - 6, 70)
  
  return (
    <Box 
      flexDirection="column" 
      borderStyle="round" 
      borderColor="gray"
      paddingX={1}
      marginY={1}
    >
      {/* Header */}
      <Box justifyContent="space-between" marginBottom={1}>
        <Text bold color="white">Tasks</Text>
        <Text dimColor>
          <Text color="green">{progressBar}</Text>
          {' '}{completedCount}/{total}
        </Text>
      </Box>
      
      {/* In Progress - highlighted */}
      {inProgress.map(item => (
        <TodoRow key={item.id} item={item} maxWidth={maxContentWidth} />
      ))}
      
      {/* Pending */}
      {pending.map(item => (
        <TodoRow key={item.id} item={item} maxWidth={maxContentWidth} />
      ))}
      
      {/* Completed - dimmed */}
      {completed.length > 0 && (
        <>
          {completed.map(item => (
            <TodoRow key={item.id} item={item} maxWidth={maxContentWidth} />
          ))}
        </>
      )}
    </Box>
  )
}

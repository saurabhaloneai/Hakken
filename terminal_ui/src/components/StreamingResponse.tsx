import React from 'react'
import { Box } from 'ink'
import { MessageBubble } from './MessageBubble.js'

interface StreamingResponseProps {
  content: string
}

export const StreamingResponse: React.FC<StreamingResponseProps> = ({ content }) => {
  if (!content) return null
  
  return (
    <Box marginBottom={1}>
      <MessageBubble label="Agent" color="magentaBright" content={content} meta="streaming" icon="◆" />
    </Box>
  )
}

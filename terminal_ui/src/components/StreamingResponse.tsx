import React from 'react'
import { Box } from 'ink'
import { MessageBubble } from './MessageBubble.js'

interface StreamingResponseProps {
  content: string
  width?: number
}

export const StreamingResponse: React.FC<StreamingResponseProps> = ({ content, width }) => {
  if (!content) return null
  
  return (
    <Box marginBottom={1}>
      <MessageBubble label="Agent" color="magentaBright" content={content} meta="streaming" icon="◆" width={width} />
    </Box>
  )
}

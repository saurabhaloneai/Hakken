import React, { useState, useEffect } from 'react'
import { Box, Text } from 'ink'

interface SpinnerProps {
  label?: string
}

const FRAMES = ['|', '/', '-', '\\']

export const Spinner: React.FC<SpinnerProps> = ({ label }) => {
  const [frame, setFrame] = useState(0)
  
  useEffect(() => {
    const timer = setInterval(() => {
      setFrame(f => (f + 1) % FRAMES.length)
    }, 100)
    return () => clearInterval(timer)
  }, [])
  
  return (
    <Box marginBottom={1}>
      <Text color="cyan">
        {FRAMES[frame]} {label || 'Processing...'}
      </Text>
    </Box>
  )
}

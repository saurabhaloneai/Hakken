import React, { useState, useEffect } from 'react'
import { Box, Text } from 'ink'

const FRAMES = ['|', '/', '-', '\\']

export const LoadingScreen: React.FC = () => {
  const [frame, setFrame] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setFrame(f => (f + 1) % FRAMES.length)
    }, 100)
    return () => clearInterval(timer)
  }, [])

  return (
    <Box flexDirection="column" alignItems="center" justifyContent="center">
      <Text bold color="white">hakken://</Text>
      <Text color="cyanBright">{FRAMES[frame]} warming up...</Text>
    </Box>
  )
}

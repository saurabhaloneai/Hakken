import { useState, useEffect } from 'react'
import { useStdout } from 'ink'

export const useTerminalWidth = (): number => {
  const { stdout } = useStdout()
  const [width, setWidth] = useState(stdout.columns || 80)
  
  useEffect(() => {
    const handleResize = () => setWidth(stdout.columns || 80)
    stdout.on('resize', handleResize)
    return () => { stdout.off('resize', handleResize) }
  }, [stdout])
  
  return width
}

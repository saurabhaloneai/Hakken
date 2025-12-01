import { useInput, useApp } from 'ink'
import { AppMode } from '../types.js'

interface KeyboardOptions {
  mode: AppMode
  hakkenOpen: boolean
  onStop: () => void
  onApprove: () => void
  onDeny: () => void
  onToggleArgs: () => void
  onToggleHakken: () => void
}

export const useKeyboard = (opts: KeyboardOptions) => {
  const { exit } = useApp()
  const { mode, hakkenOpen, onStop, onApprove, onDeny, onToggleArgs, onToggleHakken } = opts
  
  useInput((input, key) => {
    if (hakkenOpen) return
    
    if (key.escape) {
      exit()
      return
    }
    
    if (key.shift && key.tab) {
      onToggleHakken()
      return
    }
    
    if (key.ctrl && input === 's') {
      onStop()
      return
    }
    
    if (mode === 'approval') {
      if (input === 'y' || input === 'Y') onApprove()
      if (input === 'n' || input === 'N') onDeny()
      if (input === 'a' || input === 'A') onToggleArgs()
    }
  })
}

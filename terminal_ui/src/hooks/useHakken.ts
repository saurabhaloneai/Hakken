import { useState, useCallback } from 'react'
import fs from 'fs'
import path from 'path'

const HAKKEN_FILE = 'Hakken.md'
const DEFAULT_TEMPLATE = `# Hakken Instructions

Add your instructions here. The agent will follow these when working in this directory.

## Examples
- Prefer functional components
- Use TypeScript strict mode
- Always add tests for new features
`

export const useHakken = (workingDir: string) => {
  const [isOpen, setIsOpen] = useState(false)
  const [content, setContent] = useState('')
  const [isDirty, setIsDirty] = useState(false)

  const filePath = path.join(workingDir || process.cwd(), HAKKEN_FILE)

  const load = useCallback(() => {
    const exists = fs.existsSync(filePath)
    const data = exists ? fs.readFileSync(filePath, 'utf-8') : DEFAULT_TEMPLATE
    setContent(data)
    setIsDirty(!exists)
  }, [filePath])

  const open = useCallback(() => {
    load()
    setIsOpen(true)
  }, [load])

  const close = useCallback((save: boolean) => {
    if (save && content.trim()) {
      fs.writeFileSync(filePath, content, 'utf-8')
    }
    setIsOpen(false)
    setIsDirty(false)
  }, [filePath, content])

  const update = useCallback((newContent: string) => {
    setContent(newContent)
    setIsDirty(true)
  }, [])

  const toggle = useCallback(() => {
    isOpen ? close(false) : open()
  }, [isOpen, close, open])

  return { isOpen, content, isDirty, open, close, update, toggle, filePath }
}

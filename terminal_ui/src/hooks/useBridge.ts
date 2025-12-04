import { useState, useEffect, useRef } from 'react'
import { spawn, ChildProcess } from 'child_process'
import path from 'path'
import { fileURLToPath } from 'url'
import { useApp } from 'ink'
import { AppMode, Message, ToolRequest, BridgeMessage } from '../types.js'
import { TodoItem } from '../components/TodoList.js'
import { formatToolPreparing } from '../components/utils/formatToolResult.js'

export const useBridge = () => {
  const [mode, setMode] = useState<AppMode>('loading')
  const [messages, setMessages] = useState<Message[]>([])
  const [currentResponse, setCurrentResponse] = useState('')
  const [workingDir, setWorkingDir] = useState('')
  const [pendingTool, setPendingTool] = useState<ToolRequest | null>(null)
  const [statusLine, setStatusLine] = useState('')
  const [todos, setTodos] = useState<TodoItem[]>([])

  const processRef = useRef<ChildProcess | null>(null)
  const stoppingRef = useRef(false)
  const { exit } = useApp()

  const __filename = fileURLToPath(import.meta.url)
  const __dirname = path.dirname(__filename)
  const agentDir = path.join(__dirname, '..', '..')
  const pythonCmd = process.env.PYTHON || 'python3'

  const send = (msg: BridgeMessage) => {
    if (processRef.current?.stdin?.writable) {
      processRef.current.stdin.write(JSON.stringify(msg) + '\n')
    }
  }

  const appendMessage = (type: Message['type'], content?: unknown) => {
    const text = typeof content === 'string' ? content.trim() : ''
    if (!text) return
    setMessages(prev => [...prev, { type, content: text }])
  }

  const finalizeResponse = (fallback = '') => {
    setCurrentResponse(prev => {
      const final = (prev + fallback).replace(/^[\n\r]+/, '')
      if (final) {
        setMessages(msgs => [...msgs, { type: 'agent', content: final }])
      }
      return ''
    })
  }

  const handleMessage = (msg: BridgeMessage) => {
    const { type, data } = msg

    switch (type) {
      case 'ready':
        setMode('ready')
        break

      case 'environment_info':
        setWorkingDir((data.working_directory as string) || '')
        break

      case 'thinking':
        setMode('thinking')
        setStatusLine('Thinking')
        break

      case 'agent_response_chunk':
      case 'stream_chunk':
        setMode('responding')
        setCurrentResponse(prev => {
          const next = prev + (data.content as string)
          return prev === '' ? next.replace(/^\n+/, '') : next
        })
        break

      case 'agent_response_complete':
      case 'stream_end':
        finalizeResponse((data.content as string) || '')
        break

      case 'tool_request':
        setPendingTool({ name: data.name as string, args: data.args as string })
        setMode('approval')
        break

      case 'approval_request': {
        const raw = (data.content as string) || ''
        const match = raw.match(/Tool:\s*([^,]+)(?:,|$)/)
        const toolName = match?.[1]?.trim() || 'tool_execution'
        const argsText = raw.replace(/Tool:\s*[^,]+,?\s*/i, '').replace(/^args:\s*/i, '')
        setPendingTool({ name: toolName, args: argsText || raw })
        setMode('approval')
        appendMessage('system', raw)
        break
      }

      case 'tool_executing':
        setMode('executing')
        setStatusLine(`> ${data.name}`)
        break

      case 'tool_preparing': {
        setMode('executing')
        setStatusLine(`> ${data.name}`)
        const formatted = formatToolPreparing(
          data.name as string,
          (data.args || {}) as Record<string, unknown>
        )
        appendMessage('tool', formatted)
        break
      }

      case 'tool_result': {
        const name = (data.name as string) || 'tool'
        const success = data.success as boolean | undefined
        const result = typeof data.result === 'string' ? data.result : JSON.stringify(data.result)
        const status = success === false ? '[!]' : '[ok]'
        appendMessage('tool', `${status} ${name}: ${result}`)
        setStatusLine('')
        break
      }

      case 'turn_status': {
        const state = (data.state as string) || ''
        const reason = (data.reason as string) || ''
        const line = reason ? `${state}: ${reason}` : state
        setStatusLine(line)
        break
      }

      case 'stream_start':
        setMode('responding')
        setStatusLine('Responding')
        setCurrentResponse('')
        break

      case 'complete':
      case 'interrupted':
      case 'stopped':
        setMode('ready')
        setStatusLine('')
        if (type === 'stopped') {
          setMessages(prev => [...prev, { type: 'system', content: '[x] Agent stopped' }])
          setCurrentResponse('')
          setPendingTool(null)
          stoppingRef.current = false
        }
        break

      case 'error':
        appendMessage('error', (data.message as string) || (data.error as string))
        setMode('ready')
        break

      case 'message': {
        const prefix = (data.prefix as string) || ''
        const content = data.content as string
        appendMessage(prefix.includes('🤖') ? 'agent' : 'system', content)
        break
      }

      case 'assistant_message':
        finalizeResponse(data.content as string)
        break

      case 'info':
        appendMessage('system', data.content as string)
        break

      case 'todos': {
        const items = Array.isArray(data.items) ? data.items : []
        setTodos(items as TodoItem[])
        break
      }
    }
  }

  useEffect(() => {
    // Use the installed hakken module's terminal_bridge instead of relative path
    processRef.current = spawn(pythonCmd, ['-m', 'hakken.terminal_bridge'], {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: process.cwd()
    })

    let buffer = ''

    processRef.current.stdout?.on('data', (chunk: Buffer) => {
      buffer += chunk.toString()
      const regex = /__MSG__(.*?)__END__/g
      let match

      while ((match = regex.exec(buffer)) !== null) {
        const msg = JSON.parse(match[1]) as BridgeMessage
        handleMessage(msg)
      }

      const lastEnd = buffer.lastIndexOf('__END__')
      if (lastEnd !== -1) buffer = buffer.slice(lastEnd + 7)
    })

    processRef.current.on('close', () => exit())

    return () => { processRef.current?.kill() }
  }, [])

  const sendUserInput = (message: string) => {
    setMessages(prev => [...prev, { type: 'user', content: message }])
    setMode('thinking')
    send({ type: 'user_input', data: { message } })
  }

  const sendApproval = (approved: boolean, content = '') => {
    send({ type: 'tool_approval', data: { approved, content } })
    setPendingTool(null)
    setMode(approved ? 'executing' : 'ready')
    if (!approved) {
      setMessages(prev => [...prev, { type: 'system', content: `[x] Denied: ${pendingTool?.name}` }])
    }
  }

  const stopAgent = () => {
    if (!stoppingRef.current) {
      stoppingRef.current = true
      send({ type: 'stop_agent', data: {} })
      setCurrentResponse('')
      setPendingTool(null)
    }
  }

  const forceInterrupt = (message: string) => {
    send({ type: 'force_interrupt', data: { message } })
    setMessages(prev => [...prev, { type: 'user', content: message, forced: true }])
    setCurrentResponse('')
    setMode('thinking')
  }

  return {
    mode,
    messages,
    currentResponse,
    workingDir,
    pendingTool,
    statusLine,
    todos,
    stoppingRef,
    sendUserInput,
    sendApproval,
    stopAgent,
    forceInterrupt
  }
}

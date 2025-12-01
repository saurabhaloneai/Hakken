export type AppMode = 'loading' | 'ready' | 'thinking' | 'responding' | 'approval' | 'executing'

export interface Message {
  type: 'user' | 'agent' | 'tool' | 'system' | 'error'
  content: string
  queued?: boolean
  forced?: boolean
}

export interface ToolRequest {
  name: string
  args: string
}

export interface BridgeMessage {
  type: string
  data: Record<string, unknown>
}

export interface AppState {
  mode: AppMode
  messages: Message[]
  currentResponse: string
  workingDir: string
  pendingTool: ToolRequest | null
  statusLine: string
}

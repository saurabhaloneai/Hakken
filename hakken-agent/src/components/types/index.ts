export interface Message {
  type: 'user' | 'agent' | 'tool' | 'system' | 'error' | 'thinking';
  content: string;
  queued?: boolean;
  forced?: boolean;
}

export interface PendingTool {
  name: string;
  args: string;
  all_args?: any;
}

export interface PythonMessage {
  type: string;
  data: any;
}

export type AppMode = 'loading' | 'ready' | 'thinking' | 'approval';


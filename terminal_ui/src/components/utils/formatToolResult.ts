/**
 * Clean tool result formatting for terminal display.
 * Uses ASCII symbols only. No try-catch blocks.
 */

export interface FormattedResult {
  icon: string
  label: string
  summary: string
  details?: string[]
}

// ASCII-only symbols
const ICON = {
  folder: '[D]',
  file: '[F]',
  edit: '[~]',
  create: '[+]',
  delete: '[x]',
  read: '[r]',
  search: '[?]',
  grep: '[g]',
  shell: '[$]',
  git: '[git]',
  todo: '[*]',
  memory: '[m]',
  ok: '[ok]',
  err: '[!]',
  tool: '[>]',
} as const

const MAX_LEN = 60
const MAX_LINES = 6

// --- Utilities ---

const extractResult = (raw: unknown): string => {
  if (typeof raw === 'string') {
    return raw.replace(/\\n/g, '\n').replace(/\\t/g, '\t')
  }
  if (raw && typeof raw === 'object' && 'result' in raw) {
    const r = (raw as Record<string, unknown>).result
    if (typeof r === 'string') return r.replace(/\\n/g, '\n').replace(/\\t/g, '\t')
  }
  return typeof raw === 'object' ? JSON.stringify(raw) : String(raw)
}

const cut = (s: string, max: number): string => {
  const clean = s.replace(/\s+/g, ' ').trim()
  return clean.length > max ? clean.slice(0, max - 3) + '...' : clean
}

const base = (path: string): string => path.split('/').pop() || path

// --- Tool Formatters ---

const fmtListDir = (result: string): FormattedResult => {
  const lines = result.split('\n').filter(Boolean)
  const dirMatch = result.match(/Directory:\s*(.+)/)
  const totalMatch = result.match(/Total items:\s*(\d+)/)
  
  const dirName = dirMatch ? base(dirMatch[1].trim()) : 'dir'
  const total = totalMatch ? totalMatch[1] : String(lines.length)
  
  const items: string[] = []
  for (const line of lines) {
    if (line.includes('[DIR]')) items.push('  ' + ICON.folder + ' ' + line.replace(/\[DIR\]\s*/, '') + '/')
    else if (line.includes('[FILE]')) items.push('  ' + ICON.file + ' ' + line.replace(/\[FILE\]\s*/, ''))
  }
  
  return {
    icon: ICON.folder,
    label: 'list_dir',
    summary: `${dirName}/ (${total} items)`,
    details: items.length > 0 ? items.slice(0, MAX_LINES) : undefined,
  }
}

const fmtReadFile = (result: string, args?: Record<string, unknown>): FormattedResult => {
  const path = String(args?.file_path || args?.filePath || args?.path || '')
  const filename = base(path) || 'file'
  const lineCount = result.split('\n').length
  
  return { icon: ICON.read, label: 'read_file', summary: `${filename} (${lineCount} lines)` }
}

const fmtWriteFile = (result: string, args?: Record<string, unknown>): FormattedResult => {
  const path = String(args?.file_path || args?.filePath || args?.path || '')
  return { icon: ICON.create, label: 'write_file', summary: `Created ${base(path) || 'file'}` }
}

const fmtEditFile = (result: string, args?: Record<string, unknown>): FormattedResult => {
  const path = String(args?.file_path || args?.filePath || args?.path || '')
  return { icon: ICON.edit, label: 'edit_file', summary: `Modified ${base(path) || 'file'}` }
}

const fmtSearchReplace = (result: string, args?: Record<string, unknown>): FormattedResult => {
  const path = String(args?.file_path || args?.filePath || args?.path || '')
  const countMatch = result.match(/(\d+)\s*occurrence/)
  const count = countMatch ? countMatch[1] : '1'
  return { icon: ICON.edit, label: 'search_replace', summary: `${count} change(s) in ${base(path) || 'file'}` }
}

const fmtGrepSearch = (result: string, args?: Record<string, unknown>): FormattedResult => {
  const query = String(args?.query || args?.pattern || '')
  const lines = result.split('\n').filter(Boolean)
  return {
    icon: ICON.grep,
    label: 'grep_search',
    summary: `"${cut(query, 30)}" -> ${lines.length} matches`,
    details: lines.length > 0 ? lines.slice(0, MAX_LINES) : undefined,
  }
}

const fmtFileSearch = (result: string, args?: Record<string, unknown>): FormattedResult => {
  const pattern = String(args?.pattern || args?.glob || args?.query || '')
  const count = result.split('\n').filter(Boolean).length
  return { icon: ICON.search, label: 'file_search', summary: `"${cut(pattern, 30)}" -> ${count} files` }
}

const fmtSemanticSearch = (result: string, args?: Record<string, unknown>): FormattedResult => {
  const query = String(args?.query || '')
  const count = result.split('\n').filter(Boolean).length
  return { icon: ICON.search, label: 'semantic_search', summary: `"${cut(query, 30)}" -> ${count} results` }
}

const fmtShell = (result: string, args?: Record<string, unknown>): FormattedResult => {
  const lines = result.split('\n').filter(Boolean)
  const firstLine = lines[0] || 'Done'
  return {
    icon: ICON.shell,
    label: 'shell',
    summary: cut(firstLine, MAX_LEN),
    details: lines.length > 1 ? lines.slice(0, MAX_LINES) : undefined,
  }
}

const fmtGitStatus = (result: string): FormattedResult => {
  const lines = result.split('\n').filter(Boolean)
  const modified = lines.filter(l => l.includes('modified') || l.match(/^\s*M\s/)).length
  const untracked = lines.filter(l => l.includes('untracked') || l.match(/^\s*\?\s/)).length
  
  let summary = 'Clean'
  if (modified > 0 || untracked > 0) {
    const parts: string[] = []
    if (modified > 0) parts.push(`${modified} modified`)
    if (untracked > 0) parts.push(`${untracked} untracked`)
    summary = parts.join(', ')
  }
  return { icon: ICON.git, label: 'status', summary }
}

const fmtGitDiff = (result: string, args?: Record<string, unknown>): FormattedResult => {
  const file = String(args?.file || '')
  const lines = result.split('\n')
  const adds = lines.filter(l => l.startsWith('+')).length
  const dels = lines.filter(l => l.startsWith('-')).length
  const target = file ? base(file) : 'changes'
  return { icon: ICON.git, label: 'diff', summary: `${target} (+${adds}/-${dels})` }
}

const fmtGitCommit = (result: string, args?: Record<string, unknown>): FormattedResult => {
  const msg = String(args?.message || '')
  return { icon: ICON.git, label: 'commit', summary: cut(msg, MAX_LEN) || 'Committed' }
}

const fmtGitPush = (result: string): FormattedResult => {
  const ok = !result.toLowerCase().includes('error') && !result.toLowerCase().includes('rejected')
  return { icon: ICON.git, label: 'push', summary: ok ? 'Pushed' : 'Failed' }
}

const fmtTodoWrite = (result: string, args?: Record<string, unknown>): FormattedResult => {
  const action = String(args?.action || 'list')
  
  if (action === 'add') {
    const taskMatch = result.match(/Task added.*?: (.+)/)
    return { icon: ICON.todo, label: 'todo', summary: `Added: ${cut(taskMatch?.[1] || '', 40)}` }
  }
  
  if (action === 'complete') {
    const taskMatch = result.match(/marked as complete: (.+)/)
    return { icon: ICON.todo, label: 'todo', summary: `✓ ${cut(taskMatch?.[1] || 'Completed', 40)}` }
  }
  
  if (action === 'remove') {
    return { icon: ICON.todo, label: 'todo', summary: 'Task removed' }
  }
  
  const totalMatch = result.match(/Total: (\d+) pending, (\d+) completed/)
  if (totalMatch) {
    const pending = parseInt(totalMatch[1], 10)
    const completed = parseInt(totalMatch[2], 10)
    return { icon: ICON.todo, label: 'todo', summary: `${completed}/${pending + completed} done` }
  }
  
  if (result.includes('No tasks found')) {
    return { icon: ICON.todo, label: 'todo', summary: 'No tasks' }
  }
  
  return { icon: ICON.todo, label: 'todo', summary: 'Updated' }
}

const fmtMemoryAdd = (result: string, args?: Record<string, unknown>): FormattedResult => {
  const content = String(args?.content || args?.memory || '')
  return { icon: ICON.memory, label: 'memory', summary: `Added: "${cut(content, 40)}"` }
}

const fmtMemoryList = (result: string): FormattedResult => {
  const count = result.split('\n').filter(Boolean).length
  return { icon: ICON.memory, label: 'memory', summary: `${count} memories` }
}

const fmtDeleteFile = (result: string, args?: Record<string, unknown>): FormattedResult => {
  const path = String(args?.file_path || args?.filePath || args?.path || '')
  return { icon: ICON.delete, label: 'delete', summary: `Deleted ${base(path) || 'file'}` }
}

const fmtDefault = (toolName: string, result: string): FormattedResult => {
  const firstLine = result.split('\n')[0] || ''
  return { icon: ICON.tool, label: toolName, summary: cut(firstLine, MAX_LEN) || 'Done' }
}

// --- Main Export ---

export const formatToolResult = (
  toolName: string,
  rawResult: unknown,
  args?: Record<string, unknown>
): FormattedResult => {
  const result = extractResult(rawResult)
  
  const formatters: Record<string, (r: string, a?: Record<string, unknown>) => FormattedResult> = {
    list_dir: fmtListDir,
    list_directory: fmtListDir,
    read_file: fmtReadFile,
    write_file: fmtWriteFile,
    create_file: fmtWriteFile,
    edit_file: fmtEditFile,
    search_replace: fmtSearchReplace,
    grep_search: fmtGrepSearch,
    file_search: fmtFileSearch,
    semantic_search: fmtSemanticSearch,
    execute_terminal: fmtShell,
    execute_shell: fmtShell,
    run_command: fmtShell,
    shell: fmtShell,
    terminal: fmtShell,
    git_status: fmtGitStatus,
    git_diff: fmtGitDiff,
    git_commit: fmtGitCommit,
    git_push: fmtGitPush,
    todo_write: fmtTodoWrite,
    add_memory: fmtMemoryAdd,
    memory_add: fmtMemoryAdd,
    list_memory: fmtMemoryList,
    memory_list: fmtMemoryList,
    delete_file: fmtDeleteFile,
    remove_file: fmtDeleteFile,
    delete: fmtDeleteFile,
  }
  
  const formatter = formatters[toolName]
  return formatter ? formatter(result, args) : fmtDefault(toolName, result)
}

// --- Preparing Message ---

export const formatToolPreparing = (toolName: string, args: Record<string, unknown>): string => {
  if (!args || Object.keys(args).length === 0) return `${ICON.tool} ${toolName}`
  
  const path = String(args.file_path || args.filePath || args.path || args.directory || '')
  const filename = path ? base(path) : ''
  
  const formats: Record<string, () => string> = {
    read_file: () => `${ICON.read} ${filename || 'file'}`,
    write_file: () => `${ICON.create} ${filename || 'file'}`,
    create_file: () => `${ICON.create} ${filename || 'file'}`,
    edit_file: () => `${ICON.edit} ${filename || 'file'}`,
    search_replace: () => `${ICON.edit} ${filename || 'file'}`,
    delete_file: () => `${ICON.delete} ${filename || 'file'}`,
    remove_file: () => `${ICON.delete} ${filename || 'file'}`,
    list_dir: () => `${ICON.folder} ${filename || '.'}/`,
    list_directory: () => `${ICON.folder} ${filename || '.'}/`,
    grep_search: () => `${ICON.grep} "${cut(String(args.query || args.pattern || ''), 35)}"`,
    file_search: () => `${ICON.search} ${String(args.pattern || args.glob || '')}`,
    semantic_search: () => `${ICON.search} "${cut(String(args.query || ''), 35)}"`,
    execute_terminal: () => `${ICON.shell} ${cut(String(args.command || args.cmd || ''), 50)}`,
    execute_shell: () => `${ICON.shell} ${cut(String(args.command || args.cmd || ''), 50)}`,
    run_command: () => `${ICON.shell} ${cut(String(args.command || args.cmd || ''), 50)}`,
    shell: () => `${ICON.shell} ${cut(String(args.command || args.cmd || ''), 50)}`,
    terminal: () => `${ICON.shell} ${cut(String(args.command || args.cmd || ''), 50)}`,
    git_status: () => `${ICON.git} status`,
    git_diff: () => `${ICON.git} diff ${filename || ''}`,
    git_commit: () => `${ICON.git} commit "${cut(String(args.message || ''), 35)}"`,
    git_push: () => `${ICON.git} push`,
    todo_write: () => {
      const action = String(args.action || 'list')
      const task = String(args.task || '')
      if (action === 'add') return `${ICON.todo} + ${cut(task, 40)}`
      if (action === 'complete') return `${ICON.todo} ✓ completing task`
      if (action === 'remove') return `${ICON.todo} removing task`
      return `${ICON.todo} listing tasks`
    },
    add_memory: () => `${ICON.memory} adding...`,
    memory_add: () => `${ICON.memory} adding...`,
    list_memory: () => `${ICON.memory} list`,
    memory_list: () => `${ICON.memory} list`,
  }
  
  const format = formats[toolName]
  return format ? format() : `${ICON.tool} ${toolName}`
}

// --- Parse Tool Message ---

export const parseToolMessage = (content: string): { toolName: string; status: string; result: string } | null => {
  const match = content.match(/^(\[ok\]|\[!\]|ok|err)\s+(\w+):\s*(.*)$/s)
  if (!match) return null
  return { status: match[1], toolName: match[2], result: match[3] }
}

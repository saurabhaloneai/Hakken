import { useEffect, useRef, useState } from 'react';
import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
// @ts-ignore
import { useApp } from 'ink';
import { PythonMessage, Message, PendingTool, AppMode } from '../components/types/index.js';
import { toolShortLabel, truncateMiddle } from '../components/utils/stringUtils.js';

export const usePythonBridge = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [mode, setMode] = useState<AppMode>('loading');
  const [pendingTool, setPendingTool] = useState<PendingTool | null>(null);
  const [currentResponse, setCurrentResponse] = useState('');
  const [isInputDisabled, setIsInputDisabled] = useState(true);
  const [workingDirectory, setWorkingDirectory] = useState<string>('');
  const [debugInfo, setDebugInfo] = useState<string>('');
  const [statusLine, setStatusLine] = useState('');
  const pythonProcess = useRef<ChildProcess | null>(null);
  const isStoppingRef = useRef(false);
  const { exit } = useApp();

  const __filename = fileURLToPath(import.meta.url);
  const __dirname = path.dirname(__filename);
  const pythonCmd = process.env.PYTHON || path.join(__dirname, '..', '..', '..', '.venv', 'bin', 'python');

  const sendToPython = (msg: any) => {
    if (pythonProcess.current && pythonProcess.current.stdin?.writable) {
      pythonProcess.current.stdin.write(JSON.stringify(msg) + '\n');
    }
  };

  const handlePythonMessage = (msg: PythonMessage) => {
    const { type, data } = msg;
    
    switch (type) {
      case 'ready':
        setMode('ready');
        setIsInputDisabled(false);
        break;
      
      case 'environment_info':
        setWorkingDirectory(data.working_directory || '');
        break;
      
      case 'thinking':
        setMode('thinking');
        setCurrentResponse('');
        setStatusLine('Thinking');
        break;
      
      case 'agent_response_chunk':
        setCurrentResponse(prev => {
          const newContent = prev + data.content;
          return prev === '' ? newContent.replace(/^\n+/, '') : newContent;
        });
        setStatusLine('Responding');
        break;
      
      case 'agent_response_complete':
        if (currentResponse || data.content) {
          const finalContent = (currentResponse + (data.content || '')).replace(/^\n+/, '');
          setMessages(prev => [...prev, {
            type: 'agent',
            content: finalContent
          }]);
          setCurrentResponse('');
        }
        break;
      
      case 'tool_request':
        setPendingTool(data);
        setMode('approval');
        setIsInputDisabled(true);
        break;
      
      case 'tool_executing':
        const toolLabel = toolShortLabel(data.name);
        const argInfo = data.args && typeof data.args === 'string' 
          ? ` → ${truncateMiddle(data.args, 40)}` 
          : '';
        const autoApprovedBadge = data.auto_approved ? ' (auto)' : '';
        setStatusLine(`🔧 ${toolLabel}${argInfo}${autoApprovedBadge}`);
        break;
      
      case 'tool_denied':
        setMessages(prev => [...prev, {
          type: 'system',
          content: `✗ Skipped: ${data.name}`
        }]);
        break;
      
      case 'complete':
        setMode('ready');
        setIsInputDisabled(false);
        setDebugInfo('');
        setStatusLine('');
        break;
      
      case 'interrupted':
        setMode('ready');
        setIsInputDisabled(false);
        setDebugInfo('');
        setStatusLine('');
        break;
      
      case 'error':
        setMessages(prev => [...prev, {
          type: 'error',
          content: `Error: ${data.error}`
        }]);
        setMode('ready');
        setIsInputDisabled(false);
        break;
        
      case 'stopped':
        setMessages(prev => [...prev, {
          type: 'system',
          content: '[x] Agent stopped'
        }]);
        setMode('ready');
        setIsInputDisabled(false);
        isStoppingRef.current = false;
        setCurrentResponse('');
        setPendingTool(null);
        setDebugInfo('');
        setStatusLine('');
        break;
    }
  };

  useEffect(() => {
    pythonProcess.current = spawn(pythonCmd, [path.join(__dirname, '..', '..', 'src', 'bridge.py')], {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: process.cwd()
    });
    
    let buffer = '';

    pythonProcess.current.stdout?.on('data', (data: Buffer) => {
      buffer += data.toString();
      const msgRegex = /__MSG__(.*?)__END__/g;
      let match;
      
      while ((match = msgRegex.exec(buffer)) !== null) {
        try {
          const message: PythonMessage = JSON.parse(match[1]);
          handlePythonMessage(message);
        } catch (e) {
          console.error('Parse error:', e);
        }
      }

      const lastEnd = buffer.lastIndexOf('__END__');
      if (lastEnd !== -1) {
        buffer = buffer.substring(lastEnd + 7);
      }
    });
    
    pythonProcess.current.stderr?.on('data', (data: Buffer) => {
      console.error('Python stderr:', data.toString());
    });
    
    pythonProcess.current.on('close', (code: number | null) => {
      if (code !== 0) {
        console.error(`Python process exited with code ${code}`);
      }
      exit();
    });
    
    pythonProcess.current.on('error', (err: Error) => {
      console.error('Failed to start Python process:', err);
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Failed to start Python: ${err.message}`
      }]);
      setMode('ready');
      setIsInputDisabled(false);
    });

    return () => {
      if (pythonProcess.current) {
        pythonProcess.current.kill();
      }
    };
  }, []);

  const handleStopAgent = () => {
    sendToPython({
      type: 'stop_agent',
      data: {}
    });
    setCurrentResponse('');
    setPendingTool(null);
  };

  const forceSendDirect = (message: string) => {
    sendToPython({
      type: 'force_interrupt',
      data: { message }
    });
    setMessages(prev => [...prev, { 
      type: 'user', 
      content: message,
      forced: true 
    }]);
    setCurrentResponse('');
    setMode('thinking');
    setIsInputDisabled(true);
  };

  return {
    messages,
    setMessages,
    mode,
    setMode,
    pendingTool,
    setPendingTool,
    currentResponse,
    isInputDisabled,
    workingDirectory,
    debugInfo,
    setDebugInfo,
    statusLine,
    pythonProcess,
    isStoppingRef,
    sendToPython,
    handleStopAgent,
    forceSendDirect
  };
};


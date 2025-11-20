import { MutableRefObject } from 'react';
// @ts-ignore
import { useInput, useApp } from 'ink';
import { AppMode, PendingTool } from '../components/types/index.js';

interface UseKeyboardShortcutsProps {
  mode: AppMode;
  setMode: (mode: AppMode) => void;
  pendingTool: PendingTool | null;
  setPendingTool: (tool: PendingTool | null) => void;
  isStoppingRef: MutableRefObject<boolean>;
  setDebugInfo: (info: string) => void;
  handleStopAgent: () => void;
  setFocusMode: (mode: boolean | ((prev: boolean) => boolean)) => void;
  setShowToolArgs: (show: boolean | ((prev: boolean) => boolean)) => void;
  sendToPython: (msg: any) => void;
  pythonProcess: MutableRefObject<any>;
}

export const useKeyboardShortcuts = ({
  mode,
  setMode,
  pendingTool,
  setPendingTool,
  isStoppingRef,
  setDebugInfo,
  handleStopAgent,
  setFocusMode,
  setShowToolArgs,
  sendToPython,
  pythonProcess
}: UseKeyboardShortcutsProps) => {
  const { exit } = useApp();

  useInput((input: string, key: any) => {
    // Stop agent with Ctrl+S or Cmd+S
    if ((key.ctrl && input === 's') || (key.meta && input === 's')) {
      if (!isStoppingRef.current && (mode === 'thinking' || mode === 'approval')) {
        setDebugInfo(`Stopping agent...`);
        isStoppingRef.current = true;
        handleStopAgent();
      }
      return;
    }
    
    // Toggle focus mode with Ctrl+F / Cmd+F
    if ((key.ctrl && input === 'f') || (key.meta && input === 'f')) {
      setFocusMode(v => !v);
      return;
    }
    
    // Handle tool approval keys
    if (mode === 'approval' && pendingTool) {
      if (input === 'y' || input === 'Y') {
        sendToPython({
          type: 'tool_approval',
          data: { approved: true, remember: false }
        });
        setPendingTool(null);
        setMode('thinking');
      } else if (input === 'n' || input === 'N') {
        sendToPython({
          type: 'tool_approval',
          data: { approved: false, remember: false }
        });
        setPendingTool(null);
        setMode('thinking');
      } else if (input === 'a' || input === 'A') {
        sendToPython({
          type: 'tool_approval',
          data: { approved: true, remember: true }
        });
        setPendingTool(null);
        setMode('thinking');
      } else if (input === 'x' || input === 'X') {
        sendToPython({
          type: 'tool_approval',
          data: { approved: false, remember: true }
        });
        setPendingTool(null);
        setMode('thinking');
      } else if (input === 'v' || input === 'V') {
        setShowToolArgs(v => !v);
      }
      return;
    }
    
    // Exit on ESC
    if (key.escape) {
      if (pythonProcess.current) {
        pythonProcess.current.kill();
      }
      
      exit();
      
      setTimeout(() => {
        console.clear();
        console.log('\n');
        console.log('  \x1b[90m▄  █ ██   █  █▀ █  █▀ ▄███▄      ▄\x1b[0m');
        console.log(' \x1b[90m█   █ █ █  █▄█   █▄█   █▀   ▀      █\x1b[0m');
        console.log(' \x1b[90m██▀▀█ █▄▄█ █▀▄   █▀▄   ██▄▄    ██   █\x1b[0m');
        console.log(' \x1b[90m█   █ █  █ █  █  █  █  █▄   ▄▀ █ █  █\x1b[0m');
        console.log('    \x1b[90m█     █   █     █   ▀███▀   █  █ █\x1b[0m');
        console.log('   \x1b[90m▀     █   ▀     ▀            █   ██   \x1b[36mThanks for using Hakken! See you next time.\x1b[0m');
        console.log('\n');
        process.stdout.write('\x1B[?25h');
        process.exit(0);
      }, 100);
    }
  });
};


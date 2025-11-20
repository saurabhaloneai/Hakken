#!/usr/bin/env node
import React, { useState, useEffect } from 'react';
// @ts-ignore
import { render, Box } from 'ink';
import {
  Header,
  MessageItem,
  CurrentResponse,
  ThinkingIndicator,
  LoadingIndicator,
  InputBox
} from './components/index.js';
import {
  usePythonBridge,
  useTerminalSize,
  useKeyboardShortcuts,
  useQuoteRotation
} from './hooks/index.js';

const App: React.FC = () => {
  const [inputValue, setInputValue] = useState('');
  const [focusMode, setFocusMode] = useState(false);
  const [showToolArgs, setShowToolArgs] = useState(false);
  
  const {
    messages,
    setMessages,
    mode,
    setMode,
    pendingTool,
    setPendingTool,
    currentResponse,
    workingDirectory,
    debugInfo,
    setDebugInfo,
    statusLine,
    pythonProcess,
    isStoppingRef,
    sendToPython,
    handleStopAgent,
    forceSendDirect
  } = usePythonBridge();

  const terminalWidth = useTerminalSize();
  const currentQuote = useQuoteRotation(mode, currentResponse);

  useKeyboardShortcuts({
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
  });

  // Clear terminal on startup
  useEffect(() => {
    process.stdout.write('\x1Bc');
    process.stdout.write('\x1B[?25l');
    
    return () => {
      process.stdout.write('\x1B[?25h');
    };
  }, []);

  const handleSubmit = () => {
    const trimmed = inputValue.trim();
    if (!trimmed) return;

    if (trimmed.startsWith('!')) {
      const forced = trimmed.slice(1).trim();
      if (forced) {
        forceSendDirect(forced);
      }
      setInputValue('');
      return;
    }
    
    setMessages(prev => [...prev, { type: 'user', content: trimmed }]);
    
    if (mode === 'thinking' || mode === 'approval') {
      setMessages(prev => prev.map((msg, idx) => 
        idx === prev.length - 1 ? { ...msg, queued: true } : msg
      ));
    } else {
      setMode('thinking');
    }
    
    sendToPython({
      type: 'user_input',
      data: { message: trimmed }
    });
    
    setInputValue('');
  };

  const queuedCount = messages.filter(m => m.queued).length;

  return (
    <Box flexDirection="column" marginBottom={1}>
      {!focusMode && (
        <Header workingDirectory={workingDirectory} terminalWidth={terminalWidth} />
      )}
      
      {messages.map((msg, idx) => (
        <MessageItem key={idx} msg={msg} idx={idx} />
      ))}
      
      <CurrentResponse currentResponse={currentResponse} />
      
      {mode === 'thinking' && (
        <ThinkingIndicator statusLine={statusLine} quote={currentQuote} />
      )}
      
      {mode === 'loading' && <LoadingIndicator />}

      <InputBox
        mode={mode}
        inputValue={inputValue}
        setInputValue={setInputValue}
        handleSubmit={handleSubmit}
        queuedCount={queuedCount}
        pendingTool={pendingTool}
        showToolArgs={showToolArgs}
        focusMode={focusMode}
        debugInfo={debugInfo}
      />
    </Box>
  );
};

render(<App /> as any);

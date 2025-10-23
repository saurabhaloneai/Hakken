import React from 'react';
// @ts-ignore
import { Box, Text } from 'ink';
// @ts-ignore
import TextInput from 'ink-text-input';
import { AppMode, PendingTool } from './types/index.js';
import { ToolApprovalPrompt } from './ToolApprovalPrompt.js';

interface InputBoxProps {
  mode: AppMode;
  inputValue: string;
  setInputValue: (value: string) => void;
  handleSubmit: () => void;
  queuedCount: number;
  pendingTool: PendingTool | null;
  showToolArgs: boolean;
  focusMode: boolean;
  debugInfo: string;
}

export const InputBox: React.FC<InputBoxProps> = ({
  mode,
  inputValue,
  setInputValue,
  handleSubmit,
  queuedCount,
  pendingTool,
  showToolArgs,
  focusMode,
  debugInfo
}) => {
  return (
    <Box flexDirection="column" marginTop={1}>
      <Box 
        borderStyle="round" 
        borderColor={mode === 'approval' ? "yellow" : "gray"}
        paddingX={1}
        paddingY={0}
      >
        {mode === 'approval' && pendingTool ? (
          <ToolApprovalPrompt pendingTool={pendingTool} showToolArgs={showToolArgs} />
        ) : (
          <Box>
            <Text bold color="gray">{'>'}</Text>
            <Text> </Text>
            {mode === 'thinking' ? (
              <Text color="green" dimColor>
                {`Busy... (Enter=queue, Ctrl+S=stop${queuedCount ? `, ${queuedCount} queued` : ''})`}
              </Text>
            ) : (
              <TextInput
                value={inputValue}
                onChange={setInputValue}
                onSubmit={handleSubmit}
                placeholder="Type message..."
              />
            )}
          </Box>
        )}
      </Box>
      
      {!focusMode && (
        <Box flexDirection="column">
          <Text dimColor>ESC=exit | Enter=queue | Ctrl+S/Cmd+S=stop | Ctrl+F/Cmd+F=focus</Text>
          {debugInfo && <Text color="yellow" bold>[DEBUG] {debugInfo}</Text>}
        </Box>
      )}
    </Box>
  );
};


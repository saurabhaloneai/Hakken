import React from 'react';
// @ts-ignore
import { Box, Text } from 'ink';
import { PendingTool } from './types/index.js';
import { truncateMiddle } from './utils/stringUtils.js';

interface ToolApprovalPromptProps {
  pendingTool: PendingTool;
  showToolArgs: boolean;
}

export const ToolApprovalPrompt: React.FC<ToolApprovalPromptProps> = ({ pendingTool, showToolArgs }) => {
  return (
    <Box flexDirection="column">
      <Box>
        <Text bold color="yellow">🔐 Tool Permission: </Text>
        <Text bold color="white">{pendingTool.name}</Text>
      </Box>
      <Box marginTop={0}>
        <Text dimColor>
          Args: {showToolArgs 
            ? JSON.stringify(pendingTool.all_args || pendingTool.args, null, 2) 
            : truncateMiddle(pendingTool.args, 60)}
        </Text>
      </Box>
      <Box marginTop={0}>
        <Text>
          <Text color="green" bold>[Y]</Text>
          <Text color="green">es once</Text>
          <Text> • </Text>
          <Text color="red" bold>[N]</Text>
          <Text color="red">o</Text>
          <Text> • </Text>
          <Text color="cyan" bold>[A]</Text>
          <Text color="cyan">lways</Text>
          <Text> • </Text>
          <Text color="magenta" bold>[X]</Text>
          <Text color="magenta"> Never</Text>
          <Text> • </Text>
          <Text color="blue" bold>[V]</Text>
          <Text color="blue">iew full</Text>
        </Text>
      </Box>
    </Box>
  );
};


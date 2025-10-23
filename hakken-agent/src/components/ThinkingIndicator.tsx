import React from 'react';
// @ts-ignore
import { Box, Text } from 'ink';
// @ts-ignore
import Spinner from 'ink-spinner';

interface ThinkingIndicatorProps {
  statusLine: string;
  quote: string;
}

export const ThinkingIndicator: React.FC<ThinkingIndicatorProps> = ({ statusLine, quote }) => {
  return (
    <Box marginBottom={1}>
      <Text color="cyan">
        <Spinner type="dots" /> {statusLine || quote}
      </Text>
    </Box>
  );
};


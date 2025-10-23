import React, { memo } from 'react';
// @ts-ignore
import { Box, Text } from 'ink';
import { MarkdownText } from './MarkdownText.js';

interface CurrentResponseProps {
  currentResponse: string;
}

export const CurrentResponse: React.FC<CurrentResponseProps> = memo(({ currentResponse }) => {
  if (!currentResponse) return null;
  
  return (
    <Box flexDirection="column">
      <Text>
        <Text bold color="magenta">Agent: </Text>
        <Text>{String(currentResponse).split('\n')[0]}</Text>
      </Text>
      {String(currentResponse).split('\n').length > 1 && (
        <MarkdownText>{String(currentResponse).split('\n').slice(1).join('\n')}</MarkdownText>
      )}
    </Box>
  );
});

CurrentResponse.displayName = 'CurrentResponse';


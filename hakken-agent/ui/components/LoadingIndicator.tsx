import React from 'react';
// @ts-ignore
import { Box, Text } from 'ink';
// @ts-ignore
import Spinner from 'ink-spinner';

export const LoadingIndicator: React.FC = () => {
  return (
    <Box marginBottom={1}>
      <Text color="gray">
        <Spinner type="dots" /> Initializing agent...
      </Text>
    </Box>
  );
};


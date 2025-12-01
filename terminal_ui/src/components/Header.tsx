import React, { memo } from 'react';
// @ts-ignore
import { Box, Text } from 'ink';
// @ts-ignore
import { truncatePath } from './utils/stringUtils.js';

interface HeaderProps {
  workingDirectory: string;
  terminalWidth: number;
}

export const Header: React.FC<HeaderProps> = memo(({ workingDirectory, terminalWidth }) => {
  return (
    <Box flexDirection="column">
      <Box flexDirection="column">
        {terminalWidth >= 80 ? (
          <>
            <Text bold color="gray">  ▄  █ ██   █  █▀ █  █▀ ▄███▄      ▄</Text>
            <Text bold color="gray"> █   █ █ █  █▄█   █▄█   █▀   ▀      █</Text>
            <Text bold color="gray"> ██▀▀█ █▄▄█ █▀▄   █▀▄   ██▄▄    ██   █</Text>
            <Text bold color="gray"> █   █ █  █ █  █  █  █  █▄   ▄▀ █ █  █</Text>
            {workingDirectory ? (
              <>
                <Text>
                  <Text bold color="gray">    █     █   █     █   ▀███▀   █  █ █   </Text>
                  <Text color="cyan" dimColor>Working in: {truncatePath(workingDirectory, terminalWidth)}</Text>
                </Text>
                <Text bold color="gray">   ▀     █   ▀     ▀            █   ██   your autistic agent</Text>
              </>
            ) : (
              <>
                <Text bold color="gray">    █     █   █     █   ▀███▀   █  █ █</Text>
                <Text bold color="gray">   ▀     █   ▀     ▀            █   ██   your autistic agent</Text>
              </>
            )}
          </>
        ) : (
          <>
            <Text bold color="gray">HAKKEN</Text>
            <Text color="gray" dimColor>your autistic agent</Text>
            {workingDirectory && <Text color="cyan" dimColor>{truncatePath(workingDirectory, terminalWidth)}</Text>}
          </>
        )}
      </Box>
      <Text> </Text>
    </Box>
  );
});

Header.displayName = 'Header';

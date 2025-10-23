import React, { memo } from 'react';
// @ts-ignore
import { Box, Text } from 'ink';
import { Message } from './types/index.js';
import { MarkdownText } from './MarkdownText.js';

interface MessageItemProps {
  msg: Message;
  idx: number;
}

export const MessageItem: React.FC<MessageItemProps> = memo(({ msg, idx }) => {
  return (
    <Box key={idx} flexDirection="column" marginBottom={1}>
      {msg.type === 'user' && (
        <Text>
          <Text bold color="cyan">You: </Text>
          <Text color="white">{msg.content}</Text>
          {msg.queued && <Text color="yellow" dimColor> (queued)</Text>}
          {msg.forced && <Text color="red" bold> (forced)</Text>}
        </Text>
      )}
      {msg.type === 'agent' && (
        <Box flexDirection="column">
          <Text>
            <Text bold color="magenta">Agent: </Text>
            <Text>{String(msg.content).split('\n')[0]}</Text>
          </Text>
          {String(msg.content).split('\n').length > 1 && (
            <MarkdownText>{String(msg.content).split('\n').slice(1).join('\n')}</MarkdownText>
          )}
        </Box>
      )}
      {msg.type === 'tool' && (
        <Text color="blue" dimColor>  {msg.content}</Text>
      )}
      {msg.type === 'system' && (
        <Text color="gray" dimColor>  {msg.content}</Text>
      )}
      {msg.type === 'error' && (
        <Text>
          <Text color="red" bold>Error: </Text>
          <Text color="red">{msg.content}</Text>
        </Text>
      )}
    </Box>
  );
}, (prevProps, nextProps) => {
  return prevProps.msg.content === nextProps.msg.content &&
         prevProps.msg.queued === nextProps.msg.queued &&
         prevProps.msg.forced === nextProps.msg.forced &&
         prevProps.msg.type === nextProps.msg.type;
});

MessageItem.displayName = 'MessageItem';


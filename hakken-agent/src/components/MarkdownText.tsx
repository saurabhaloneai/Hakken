import React, { memo } from 'react';
// @ts-ignore
import { Box, Text } from 'ink';

interface MarkdownTextProps {
  children: string;
}

export const MarkdownText: React.FC<MarkdownTextProps> = memo(({ children }) => {
  const renderInline = (text: string): React.ReactNode[] => {
    const codeSplit = text.split(/(`[^`]+`)/g);
    const nodes: React.ReactNode[] = [];
    for (let i = 0; i < codeSplit.length; i++) {
      const segment = codeSplit[i];
      if (segment.startsWith('`') && segment.endsWith('`')) {
        nodes.push(<Text key={`code-${i}`} color="yellow">{segment.slice(1, -1)}</Text>);
      } else {
        const boldSplit = segment.split(/(\*\*[^*]+\*\*)/g);
        for (let j = 0; j < boldSplit.length; j++) {
          const part = boldSplit[j];
          if (part.startsWith('**') && part.endsWith('**')) {
            nodes.push(<Text key={`b-${i}-${j}`} bold>{part.slice(2, -2)}</Text>);
          } else {
            nodes.push(<Text key={`t-${i}-${j}`}>{part}</Text>);
          }
        }
      }
    }
    return nodes;
  };

  const lines = children.split('\n');
  const transformed: React.ReactNode[] = [];
  let inCodeBlock = false;
  let previousWasHeading = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (trimmed.startsWith('```')) {
      inCodeBlock = !inCodeBlock;
      continue;
    }

    if (inCodeBlock) {
      transformed.push(<Text key={`code-${i}`} color="yellow">{line}</Text>);
      previousWasHeading = false;
      continue;
    }

    if (/^\s*#{1,6}\s+/.test(line)) {
      if (!previousWasHeading && transformed.length > 0) {
        transformed.push(<Text key={`sp-h-${i}`}> </Text>);
      }
      transformed.push(
        <Text key={`h-${i}`} bold color="cyan">{line.replace(/^\s*#{1,6}\s+/, '')}</Text>
      );
      previousWasHeading = true;
      continue;
    }

    previousWasHeading = false;

    const orderedMatch = line.match(/^(\s*)(\d+)\.\s+(.*)$/);
    if (orderedMatch) {
      const indent = orderedMatch[1] || '';
      const num = orderedMatch[2];
      const content = orderedMatch[3];
      transformed.push(
        <Text key={`ol-${i}`}>{indent}{num}. <Text>{renderInline(content)}</Text></Text>
      );
      continue;
    }

    if (/^\s*[-*]\s+/.test(line)) {
      const content = line.replace(/^\s*[-*]\s+/, '');
      transformed.push(
        <Text key={`ul-${i}`}>  • <Text>{renderInline(content)}</Text></Text>
      );
      continue;
    }

    if (trimmed.length === 0) {
      transformed.push(<Text key={`blank-${i}`}> </Text>);
      continue;
    }

    transformed.push(
      <Text key={`p-${i}`}>{renderInline(line)}</Text>
    );
  }

  return <Box flexDirection="column">{transformed}</Box>;
});

MarkdownText.displayName = 'MarkdownText';


import { TOOL_LABELS } from './constants.js';

export const truncateMiddle = (s: string, max: number = 80): string => {
  if (!s) return '';
  if (s.length <= max) return s;
  const keep = Math.floor(max / 2) - 1;
  return s.slice(0, keep) + '…' + s.slice(-keep);
};

export const truncatePath = (path: string, terminalWidth: number): string => {
  const maxLength = Math.min(60, terminalWidth - 20);
  if (path.length <= maxLength) {
    return path;
  }
  return '...' + path.slice(-(maxLength - 3));
};

export const toolShortLabel = (toolName: string): string => {
  const pretty = TOOL_LABELS[toolName] || toolName.replace(/_/g, ' ');
  return pretty.split(' ').slice(0, 3).join(' ');
};


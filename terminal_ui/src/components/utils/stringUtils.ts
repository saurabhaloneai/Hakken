export const truncatePath = (path: string, maxLen: number): string => {
  if (path.length <= maxLen) return path;
  const parts = path.split('/');
  if (parts.length <= 2) return '...' + path.slice(-maxLen + 3);
  return '.../' + parts.slice(-2).join('/');
};

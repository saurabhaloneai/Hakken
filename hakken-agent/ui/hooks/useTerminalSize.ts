import { useState, useEffect } from 'react';

export const useTerminalSize = () => {
  const [terminalWidth, setTerminalWidth] = useState(process.stdout.columns || 80);
  
  useEffect(() => {
    const handleResize = () => {
      setTerminalWidth(process.stdout.columns || 80);
    };
    process.stdout.on('resize', handleResize);
    return () => {
      process.stdout.off('resize', handleResize);
    };
  }, []);

  return terminalWidth;
};


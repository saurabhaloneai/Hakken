import { useState, useEffect } from 'react';
import { WORKING_QUOTES } from '../components/utils/constants.js';
import { AppMode } from '../components/types/index.js';

export const useQuoteRotation = (mode: AppMode, currentResponse: string) => {
  const [currentQuoteIndex, setCurrentQuoteIndex] = useState(0);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (mode === 'thinking' && !currentResponse) {
      interval = setInterval(() => {
        setCurrentQuoteIndex(prev => (prev + 1) % WORKING_QUOTES.length);
      }, 2000);
    }
    
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [mode, currentResponse]);

  return WORKING_QUOTES[currentQuoteIndex];
};


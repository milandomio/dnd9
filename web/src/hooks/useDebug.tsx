import { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import type { AdjState } from '../components/MapDebug';

interface DebugContextType {
  debug: boolean;
  toggle: () => void;
  adjOffsets: AdjState;
  setAdjOffsets: React.Dispatch<React.SetStateAction<AdjState>>;
}

const DebugContext = createContext<DebugContextType | null>(null);

export function DebugProvider({ children }: { children: ReactNode }) {
  const [debug, setDebug] = useState(false);
  const [adjOffsets, setAdjOffsets] = useState<AdjState>({});

  const toggle = useCallback(() => setDebug((d) => !d), []);

  return (
    <DebugContext.Provider value={{ debug, toggle, adjOffsets, setAdjOffsets }}>
      {children}
    </DebugContext.Provider>
  );
}

export function useDebug() {
  const ctx = useContext(DebugContext);
  if (!ctx) throw new Error('useDebug must be used within DebugProvider');
  return ctx;
}

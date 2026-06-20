import { createContext, useContext, useState, useRef, useCallback, type ReactNode } from 'react';

interface LoadingBarContextType {
  start: () => void;
  stop: () => void;
  isVisible: boolean;
}

const LoadingBarContext = createContext<LoadingBarContextType>({
  start: () => {},
  stop: () => {},
  isVisible: false,
});

export function useLoadingBar(): LoadingBarContextType {
  return useContext(LoadingBarContext);
}

export function LoadingBarProvider({ children }: { children: ReactNode }) {
  const [isVisible, setIsVisible] = useState(false);
  const [progress, setProgress] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const start = useCallback(() => {
    setIsVisible(true);
    setProgress(10);
    timerRef.current = setInterval(() => {
      setProgress(prev => Math.min(prev + (100 - prev) * 0.08, 90));
    }, 200);
  }, []);

  const stop = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    setProgress(100);
    setTimeout(() => { setIsVisible(false); setProgress(0); }, 400);
  }, []);

  return (
    <LoadingBarContext.Provider value={{ start, stop, isVisible }}>
      {isVisible && (
        <div className="fixed top-0 left-0 right-0 z-[9999] h-[2px]">
          <div className="h-full bg-gradient-to-r from-[var(--color-accent-cyan)] to-[var(--color-accent-violet)] shadow-[0_0_8px_rgba(6,182,212,0.6)] transition-all duration-300 ease-out"
            style={{ width: `${progress}%` }} />
        </div>
      )}
      {children}
    </LoadingBarContext.Provider>
  );
}

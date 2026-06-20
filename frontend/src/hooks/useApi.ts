import { useState, useEffect, useCallback, useRef } from 'react';

export type ApiState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T; timestamp: number }
  | { status: 'error'; error: string; retryCount: number };

interface UseApiOptions {
  immediate?: boolean;
  retries?: number;
  retryDelay?: number;
}

export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: React.DependencyList = [],
  options: UseApiOptions = {}
) {
  const { immediate = true, retries = 2, retryDelay = 1000 } = options;
  const [state, setState] = useState<ApiState<T>>({ status: 'idle' });
  const mountedRef = useRef(true);
  const retryCountRef = useRef(0);

  const execute = useCallback(async () => {
    setState({ status: 'loading' });
    try {
      const data = await fetcher();
      if (!mountedRef.current) return;
      setState({ status: 'success', data, timestamp: Date.now() });
      retryCountRef.current = 0;
    } catch (err) {
      if (!mountedRef.current) return;
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      if (retryCountRef.current < retries) {
        retryCountRef.current++;
        setTimeout(execute, retryDelay * retryCountRef.current);
      } else {
        setState({ status: 'error', error: errorMsg, retryCount: retryCountRef.current });
        retryCountRef.current = 0;
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    mountedRef.current = true;
    if (immediate) execute();
    return () => { mountedRef.current = false; };
  }, [execute, immediate]);

  return { state, refetch: execute };
}

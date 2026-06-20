import { useEffect } from 'react';

type Modifier = 'ctrl' | 'meta' | 'shift' | 'alt';

export function useKeyboardShortcut(
  key: string,
  callback: () => void,
  modifiers: Modifier[] = []
) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const modOk = modifiers.every(mod => {
        if (mod === 'ctrl') return e.ctrlKey;
        if (mod === 'meta') return e.metaKey;
        if (mod === 'shift') return e.shiftKey;
        if (mod === 'alt') return e.altKey;
        return false;
      });
      if (modOk && e.key.toLowerCase() === key.toLowerCase()) {
        e.preventDefault();
        callback();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [key, callback, modifiers]);
}

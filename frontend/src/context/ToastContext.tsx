import { createContext, useContext, useState, useCallback, ReactNode } from 'react';

type ToastVariant = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: number;
  message: string;
  variant: ToastVariant;
  dismissed: boolean;
}

interface ToastContextValue {
  toasts: Toast[];
  show: (message: string, variant?: ToastVariant) => void;
  dismiss: (id: number) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

const VARIANTS: Record<ToastVariant, { bg: string; border: string; icon: string }> = {
  success: { bg: 'rgba(0,255,157,0.1)', border: 'rgba(0,255,157,0.3)', icon: '✓' },
  error: { bg: 'rgba(255,61,110,0.1)', border: 'rgba(255,61,110,0.3)', icon: '✕' },
  warning: { bg: 'rgba(255,184,0,0.1)', border: 'rgba(255,184,0,0.3)', icon: '⚠' },
  info: { bg: 'rgba(0,240,255,0.1)', border: 'rgba(0,240,255,0.3)', icon: 'ℹ' },
};

let toastId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts(prev => prev.map(t => t.id === id ? { ...t, dismissed: true } : t));
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 300);
  }, []);

  const show = useCallback((message: string, variant: ToastVariant = 'info') => {
    const id = ++toastId;
    setToasts(prev => [...prev, { id, message, variant, dismissed: false }]);
    setTimeout(() => dismiss(id), 4000);
  }, [dismiss]);

  return (
    <ToastContext.Provider value={{ toasts, show, dismiss }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none">
        {toasts.map(t => (
          <div
            key={t.id}
            style={{
              background: VARIANTS[t.variant].bg,
              borderColor: VARIANTS[t.variant].border,
              transform: t.dismissed ? 'translateX(120%) scale(0.9)' : 'translateX(0) scale(1)',
              opacity: t.dismissed ? 0 : 1,
              transition: 'transform 300ms cubic-bezier(0.4,0,0.2,1), opacity 300ms cubic-bezier(0.4,0,0.2,1)',
            }}
            className="pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-xl shadow-2xl min-w-[320px] max-w-[420px]"
          >
            <span className="text-lg font-mono">{VARIANTS[t.variant].icon}</span>
            <p className="text-sm text-[var(--color-text-primary)] flex-1">{t.message}</p>
            <button
              onClick={() => dismiss(t.id)}
              className="text-[var(--color-text-muted)] hover:text-white transition-colors text-lg leading-none"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

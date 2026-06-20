interface PipelineStep {
  label: string;
  status: 'pending' | 'running' | 'done';
}

interface Props {
  steps: PipelineStep[];
  title?: string;
}

export default function PipelineVisualizer({ steps, title }: Props) {
  return (
    <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-4">
      {title && (
        <p className="text-xs font-mono text-[var(--color-text-muted)] uppercase tracking-wider mb-3">{title}</p>
      )}
      <div className="space-y-2">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-3 text-sm">
            <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 text-[10px] font-mono font-bold"
              style={{
                background: step.status === 'done' ? 'rgba(0,255,157,0.2)' : step.status === 'running' ? 'rgba(0,240,255,0.2)' : 'rgba(255,255,255,0.05)',
                color: step.status === 'done' ? 'var(--color-accent-emerald)' : step.status === 'running' ? 'var(--color-accent-cyan)' : 'var(--color-text-muted)',
                boxShadow: step.status === 'running' ? '0 0 12px rgba(0,240,255,0.3)' : 'none',
              }}
            >
              {step.status === 'done' ? '✓' : step.status === 'running' ? '▸' : String(i + 1)}
            </div>
            <span style={{
              color: step.status === 'done' ? 'var(--color-text-primary)' : step.status === 'running' ? 'var(--color-accent-cyan)' : 'var(--color-text-muted)',
              fontWeight: step.status === 'running' ? 600 : 400,
            }}>
              {step.label}
            </span>
            {step.status === 'running' && (
              <span className="ml-auto flex gap-0.5">
                <span className="w-1 h-1 rounded-full bg-[var(--color-accent-cyan)] animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1 h-1 rounded-full bg-[var(--color-accent-cyan)] animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1 h-1 rounded-full bg-[var(--color-accent-cyan)] animate-bounce" style={{ animationDelay: '300ms' }} />
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

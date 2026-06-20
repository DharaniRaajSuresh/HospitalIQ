type Status = 'ml_model' | 'db_trend' | 'estimated' | 'live' | 'cached';

interface Props {
  status: Status;
  label?: string;
}

const CONFIG: Record<Status, { color: string; pulse?: boolean; defaultLabel: string }> = {
  ml_model: { color: 'var(--color-accent-emerald)', defaultLabel: 'ML Model' },
  db_trend: { color: 'var(--color-accent-amber)', defaultLabel: 'DB Trend' },
  estimated: { color: 'var(--color-accent-rose)', defaultLabel: 'Estimated' },
  live: { color: 'var(--color-accent-cyan)', pulse: true, defaultLabel: 'Live' },
  cached: { color: 'var(--color-text-muted)', defaultLabel: 'Cached' },
};

export default function StatusBadge({ status, label }: Props) {
  const cfg = CONFIG[status];
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-mono font-medium px-2 py-1 rounded-full"
      style={{ background: `${cfg.color}15`, color: cfg.color, border: `1px solid ${cfg.color}30` }}
    >
      <span style={{
        display: 'inline-block',
        width: 6,
        height: 6,
        borderRadius: '50%',
        background: cfg.color,
        boxShadow: cfg.pulse ? `0 0 6px ${cfg.color}` : 'none',
        animation: cfg.pulse ? 'pulse-dot 2s ease-in-out infinite' : 'none',
      }} />
      {label || cfg.defaultLabel}
      <style>{`
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(0.8); }
        }
      `}</style>
    </span>
  );
}

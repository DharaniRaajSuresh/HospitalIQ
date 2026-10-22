interface Props {
  variant?: 'card' | 'table-row' | 'chart' | 'stat-card' | 'text';
  rows?: number;
  className?: string;
}

const shimmerStyle = {
  background: 'linear-gradient(90deg, var(--color-surface-3) 25%, rgba(255,255,255,0.08) 50%, var(--color-surface-3) 75%)',
  backgroundSize: '200% 100%',
  animation: 'shimmer 1.5s ease-in-out infinite',
  borderRadius: '8px',
};

const VARIANTS: Record<string, React.CSSProperties> = {
  card: { height: '180px', width: '100%' },
  'table-row': { height: '48px', width: '100%' },
  chart: { height: '300px', width: '100%' },
  'stat-card': { height: '120px', width: '100%' },
  text: { height: '16px', width: '60%' },
};

export default function SkeletonLoader({ variant = 'card', rows = 1, className = '' }: Props) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} style={{ ...shimmerStyle, ...VARIANTS[variant] }} />
      ))}
      <style>{`
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  );
}

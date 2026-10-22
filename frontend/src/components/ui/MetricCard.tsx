import { useEffect, useRef, ReactNode } from 'react';

interface Props {
  label: string;
  value: number;
  icon?: ReactNode;
  delta?: number;
  deltaLabel?: string;
  sparklineData?: number[];
  format?: (v: number) => string;
  color?: string;
  suffix?: string;
}

function animateValue(
  start: number,
  end: number,
  duration: number,
  onUpdate: (v: number) => void,
  easing: 'easeOutExpo' | 'linear' = 'easeOutExpo'
) {
  const startTime = performance.now();
  const ease = (t: number) => easing === 'easeOutExpo' ? (t === 1 ? 1 : 1 - Math.pow(2, -10 * t)) : t;

  const tick = (now: number) => {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const currentValue = start + (end - start) * ease(progress);
    onUpdate(Math.round(currentValue));
    if (progress < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

export default function MetricCard({ label, value, icon, delta, deltaLabel, sparklineData, format, color = 'var(--color-accent-cyan)', suffix = '' }: Props) {
  const displayRef = useRef<HTMLSpanElement>(null);
  const hasAnimated = useRef(false);

  useEffect(() => {
    if (hasAnimated.current || !displayRef.current) return;
    hasAnimated.current = true;
    const start = 0;
    animateValue(start, value, 1200, (v) => {
      if (displayRef.current) {
        displayRef.current.textContent = format ? format(v) : `${v.toLocaleString()}${suffix}`;
      }
    });
  }, [value, format, suffix]);

  const deltaColor = delta !== undefined ? (delta >= 0 ? 'var(--color-accent-emerald)' : 'var(--color-accent-rose)') : undefined;

  return (
    <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-4 hover:border-[var(--color-border-strong)] transition-all duration-[var(--transition-fast)]"
      style={{ borderLeft: `3px solid ${color}` }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider">{label}</span>
        {icon && <span style={{ color }} className="w-4 h-4 flex items-center">{icon}</span>}
      </div>
      <div className="flex items-baseline gap-2">
        <span ref={displayRef} className="text-2xl font-bold font-heading text-[var(--color-text-primary)]">
          {format ? format(value) : `${value.toLocaleString()}${suffix}`}
        </span>
        {delta !== undefined && (
          <span style={{ color: deltaColor }} className="text-xs font-mono font-medium">
            {delta >= 0 ? '↑' : '↓'} {Math.abs(delta).toFixed(1)}%
            {deltaLabel && <span className="text-[var(--color-text-muted)] ml-1">{deltaLabel}</span>}
          </span>
        )}
      </div>
      {sparklineData && sparklineData.length > 1 && (
        <svg viewBox={`0 0 ${sparklineData.length - 1} 20`} className="w-full h-5 mt-2" preserveAspectRatio="none">
          <polyline
            points={sparklineData.map((v, i) => `${i},${20 - (v / (Math.max(...sparklineData) || 1)) * 18}`).join(' ')}
            fill="none"
            stroke={color}
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ opacity: 0.6 }}
          />
        </svg>
      )}
    </div>
  );
}

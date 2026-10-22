import React from 'react';
import GlassCard from './GlassCard';
import AnimatedCounter from './AnimatedCounter';
import { cn } from '../../lib/utils';

function fmt(v) {
  if (v == null || v === '—') return '—';
  if (typeof v === 'number') return v.toLocaleString();
  const n = Number(v);
  return isNaN(n) ? v : n.toLocaleString();
}

const KPICard = ({ label, value, icon: Icon, color = 'cyan', trend = 0, prefix = '', suffix = '' }) => {
  const colors = {
    cyan: 'text-cyan-400 bg-cyan-400/10',
    emerald: 'text-emerald-400 bg-emerald-400/10',
    violet: 'text-violet-400 bg-violet-400/10',
    blue: 'text-blue-400 bg-blue-400/10',
    amber: 'text-amber-400 bg-amber-400/10',
    rose: 'text-rose-400 bg-rose-400/10'
  };

  return (
    <GlassCard className="relative group flex flex-col gap-4">
      <div className={cn(
        "absolute -right-16 -top-16 w-40 h-40 rounded-full blur-[60px] opacity-30 transition-all duration-700 group-hover:opacity-60 group-hover:scale-110",
        color === 'cyan' && 'bg-cyan-500',
        color === 'emerald' && 'bg-emerald-500',
        color === 'violet' && 'bg-violet-500',
        color === 'blue' && 'bg-blue-500',
        color === 'amber' && 'bg-amber-500',
        color === 'rose' && 'bg-rose-500'
      )} />

      <div className="flex justify-between items-start relative z-10 gap-2">
        <span className="text-secondary font-medium tracking-wide text-sm leading-tight">{label}</span>
        {Icon && (
          <div className={cn("p-2 rounded-lg shrink-0", colors[color] || colors.cyan)}>
            <Icon size={20} />
          </div>
        )}
      </div>

      <div className="flex flex-col relative z-10 mt-2 gap-1 w-full overflow-hidden">
        <span className="text-2xl font-bold text-primary tracking-tight whitespace-nowrap">
          {value === '—' ? value : <AnimatedCounter value={value} />}
        </span>

        <div className="flex items-center justify-start min-h-[1.25rem]">
          {typeof trend === 'number' && trend !== 0 && (
            <span className="text-sm font-medium">{trend > 0 ? '+' : ''}{trend}%</span>
          )}
          {typeof trend === 'string' && trend && (
            <span className="text-xs text-[var(--color-text-muted)] leading-tight truncate">{trend}</span>
          )}
        </div>
      </div>
    </GlassCard>
  );
};

export default KPICard;


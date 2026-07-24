import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ReferenceDot } from 'recharts';
import { AlertTriangle, Info, ShieldCheck, Activity } from 'lucide-react';

const DATA_POINTS = [
  { months: 3, mape: 2847 },
  { months: 6, mape: 1204 },
  { months: 12, mape: 156 },
  { months: 24, mape: 48.2 },
  { months: 36, mape: 28.7 },
  { months: 48, mape: 19.3 },
  { months: 60, mape: 14.8 },
  { months: 84, mape: 12.1 },
  { months: 120, mape: 11.2 }
];

function interpolateMape(months: number) {
  if (months <= DATA_POINTS[0].months) return DATA_POINTS[0].mape;
  if (months >= DATA_POINTS[DATA_POINTS.length - 1].months) return DATA_POINTS[DATA_POINTS.length - 1].mape;
  
  for (let i = 0; i < DATA_POINTS.length - 1; i++) {
    const p1 = DATA_POINTS[i];
    const p2 = DATA_POINTS[i + 1];
    if (months >= p1.months && months <= p2.months) {
      const ratio = (months - p1.months) / (p2.months - p1.months);
      return p1.mape + ratio * (p2.mape - p1.mape);
    }
  }
  return 0;
}

export default function FewShotSimulator() {
  const [months, setMonths] = useState(24);
  
  useEffect(() => { document.title = 'Few-Shot Calibration | HOSPi'; }, []);

  const currentMape = useMemo(() => interpolateMape(months), [months]);

  const getColor = (mape: number) => {
    if (mape > 100) return 'var(--color-accent-rose)';
    if (mape > 30) return 'var(--color-accent-amber)';
    return 'var(--color-accent-emerald)';
  };

  const getInsight = (m: number) => {
    if (m < 12) return { text: "Critical failure. Model outputs random noise. Cannot be used for novel pathogens.", icon: <AlertTriangle className="w-5 h-5" />, color: 'var(--color-accent-rose)' };
    if (m < 36) return { text: "Poor calibration. High risk of false predictions, but general trend direction might be visible.", icon: <Activity className="w-5 h-5" />, color: 'var(--color-accent-amber)' };
    if (m < 60) return { text: "Acceptable for long-term trends, but short-term volatility still exists. Needs careful monitoring.", icon: <Info className="w-5 h-5" />, color: 'var(--color-accent-cyan)' };
    return { text: "Optimized. Good calibration achieved. Predictions are stable.", icon: <ShieldCheck className="w-5 h-5" />, color: 'var(--color-accent-emerald)' };
  };

  const color = getColor(currentMape);
  const insight = getInsight(months);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white tracking-tight">Few-Shot Calibration Simulator</h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          Explore how the amount of historical training data impacts XGBoost model error rates (MAPE).
        </p>
      </div>

      <AnimatePresence>
        {months < 12 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="bg-[var(--color-accent-rose)]/10 border border-[var(--color-accent-rose)]/30 rounded-xl p-4 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-[var(--color-accent-rose)] shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-bold text-[var(--color-accent-rose)]">⚠️ CATASTROPHIC FAILURE</h3>
                <p className="text-xs text-[var(--color-accent-rose)]/80 mt-1">
                  Model fails completely with &lt; 12 months of data. This undermines pandemic preparedness claims for novel pathogens where historical data is unavailable.
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Controls & Metrics */}
        <div className="space-y-6">
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-6">
            <h2 className="text-sm font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-4">Training Data Available</h2>
            <div className="flex items-end justify-between mb-2">
              <span className="text-3xl font-bold text-white">{months}</span>
              <span className="text-sm text-[var(--color-text-muted)] mb-1">Months</span>
            </div>
            
            <input
              type="range"
              min={3}
              max={120}
              step={1}
              value={months}
              onChange={(e) => setMonths(Number(e.target.value))}
              className="w-full h-2 bg-[var(--color-border-subtle)] rounded-lg appearance-none cursor-pointer accent-[var(--color-accent-cyan)] mt-4"
            />
            <div className="flex justify-between text-[10px] text-[var(--color-text-muted)] mt-2 font-mono">
              <span>3m</span>
              <span>120m</span>
            </div>
          </div>

          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-6 text-center">
            <h2 className="text-sm font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Current Model Error</h2>
            <motion.div 
              key={currentMape}
              initial={{ scale: 0.9, opacity: 0.8 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: 'spring', stiffness: 200, damping: 10 }}
              className="text-5xl font-bold my-4 font-mono"
              style={{ color }}
            >
              {currentMape.toFixed(1)}%
            </motion.div>
            <p className="text-xs text-[var(--color-text-muted)]">Mean Absolute Percentage Error (MAPE)</p>
          </div>

          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-5">
            <div className="flex items-start gap-3" style={{ color: insight.color }}>
              <div className="mt-0.5">{insight.icon}</div>
              <p className="text-xs leading-relaxed">{insight.text}</p>
            </div>
          </div>
        </div>

        {/* Chart */}
        <div className="md:col-span-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-5">
          <h2 className="text-sm font-semibold text-white mb-6">Learning Curve (Months vs MAPE)</h2>
          <div className="h-[350px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={DATA_POINTS} margin={{ top: 10, right: 20, left: 10, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" vertical={false} />
                <XAxis 
                  dataKey="months" 
                  type="number"
                  domain={[0, 120]}
                  stroke="var(--color-text-muted)" 
                  tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }} 
                  label={{ value: 'Months of Training Data', position: 'insideBottom', offset: -5, fill: 'var(--color-text-muted)', fontSize: 12 }}
                />
                <YAxis 
                  stroke="var(--color-text-muted)" 
                  tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }} 
                  unit="%" 
                  domain={[0, 3000]}
                  scale="log"
                  allowDataOverflow
                  ticks={[10, 30, 100, 300, 1000, 3000]}
                />
                <Tooltip
                  contentStyle={{ background: 'rgba(11,17,32,0.9)', border: '1px solid var(--color-border-subtle)', borderRadius: '8px' }}
                  itemStyle={{ fontSize: '12px', color: 'var(--color-accent-cyan)' }}
                  labelStyle={{ color: 'var(--color-text-muted)' }}
                  formatter={(val?: string | number | readonly (string | number)[]) => [`${Number(val ?? 0).toFixed(1)}%`, 'MAPE']}
                  labelFormatter={(val) => `${val} Months`}
                />
                <Line 
                  type="monotone" 
                  dataKey="mape" 
                  stroke="var(--color-accent-cyan)" 
                  strokeWidth={3} 
                  dot={{ fill: 'var(--color-surface-1)', stroke: 'var(--color-accent-cyan)', strokeWidth: 2, r: 4 }} 
                  activeDot={{ r: 6, fill: 'var(--color-accent-cyan)' }}
                />
                <ReferenceLine x={months} stroke={color} strokeDasharray="3 3" />
                <ReferenceDot x={months} y={currentMape} r={6} fill={color} stroke="var(--color-surface-1)" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}

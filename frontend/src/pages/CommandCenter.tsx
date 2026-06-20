import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  BedDouble, Activity, Building2, AlertTriangle, TrendingUp, Sparkles,
  MapPin, Clock, Users, Download, ArrowRight, ChevronRight, X
} from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from 'recharts';
import { getStats, getLocationStats, getStates } from '../api';
import { useApi } from '../hooks/useApi';
import { StatsResponse, LocationStatsResponse } from '../types/api';
import MetricCard from '../components/ui/MetricCard';
import StatusBadge from '../components/ui/StatusBadge';
import SkeletonLoader from '../components/ui/SkeletonLoader';
import { useKeyboardShortcut } from '../hooks/useKeyboardShortcut';
import CommandPalette from '../components/ui/CommandPalette';

const SPARKLINE_DATA = [65, 72, 68, 78, 82, 76, 80, 85, 82, 88, 84, 90];

function useISTClock() {
  const [time, setTime] = useState('');
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
      setTime(ist.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return time;
}

function useSystemHealth() {
  const [health, setHealth] = useState<{ api: boolean; db: boolean; ml: boolean }>({ api: true, db: true, ml: true });
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch('/api/v1/health/ready');
        const data = await res.json();
        setHealth({ api: data.status === 'healthy', db: data.database === 'connected', ml: (data.models_loaded || 0) > 0 });
      } catch {
        setHealth({ api: false, db: false, ml: false });
      }
    };
    check();
    const id = setInterval(check, 30000);
    return () => clearInterval(id);
  }, []);
  return health;
}

interface AlertItem {
  id: number;
  severity: 'critical' | 'warning' | 'info' | 'success';
  message: string;
  state: string;
  time: string;
}

function generateAlerts(stats: StatsResponse | null, locationStats: LocationStatsResponse | null): AlertItem[] {
  const alerts: AlertItem[] = [];
  if (stats) {
    alerts.push(
      { id: 1, severity: 'info', message: `${stats.districts} districts across ${stats.states} states tracked`, state: 'All India', time: '2 min ago' },
      { id: 2, severity: 'success', message: `${stats.beds.toLocaleString()} bed records processed`, state: 'System', time: '5 min ago' },
      { id: 3, severity: 'info', message: `${stats.mortality_records.toLocaleString()} mortality records analyzed`, state: 'System', time: '8 min ago' },
    );
  }
  if (locationStats?.hospitals) {
    const sr = locationStats.hospitals.avg_success_rate;
    if (sr && sr > 75) alerts.push({ id: 4, severity: 'success', message: `National avg success rate: ${sr.toFixed(1)}%`, state: 'All India', time: '12 min ago' });
  }
  if (locationStats?.beds) {
    const occ = locationStats.beds.avg_occupancy;
    if (occ && occ > 80) alerts.push({ id: 5, severity: 'warning', message: `Bed occupancy at ${occ.toFixed(1)}% — above threshold`, state: 'All India', time: '15 min ago' });
  }
  return alerts;
}

export default function CommandCenter() {
  useEffect(() => { document.title = 'Command Center | HOSPi'; }, []);
  const navigate = useNavigate();
  const istTime = useISTClock();
  const health = useSystemHealth();
  const [commandOpen, setCommandOpen] = useState(false);
  const [selectedState, setSelectedState] = useState<string | null>(null);
  const [regionChartData, setRegionChartData] = useState<{ name: string; beds: number; hospitals: number; occupancy: number }[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);

  const statsApi = useApi(() => getStats<StatsResponse>(), []);
  const locApi = useApi(() => getLocationStats<LocationStatsResponse>('', '').catch(() => null), []);

  useKeyboardShortcut('k', () => setCommandOpen(true), ['meta']);
  useKeyboardShortcut('k', () => setCommandOpen(true), ['ctrl']);

  useEffect(() => {
    if (statsApi.state.status === 'success' || locApi.state.status === 'success') {
      const s = statsApi.state.status === 'success' ? statsApi.state.data : null;
      const l = locApi.state.status === 'success' ? locApi.state.data : null;
      setAlerts(generateAlerts(s, l));
    }
  }, [statsApi.state.status, locApi.state.status]);

  // Fetch state-level data for chart
  useEffect(() => {
    getStates<string[]>().then(async (states) => {
      const results = await Promise.allSettled(
        states.slice(0, 10).map(s => getLocationStats<LocationStatsResponse>(s, '').catch(() => null))
      );
      const data = results
        .filter(r => r.status === 'fulfilled' && r.value)
        .map(r => (r as PromiseFulfilledResult<LocationStatsResponse>).value)
        .filter(Boolean)
        .map(d => ({
          name: d.state || 'Unknown',
          beds: d.beds?.total_beds || 0,
          hospitals: d.hospitals?.total || 0,
          occupancy: d.beds?.avg_occupancy || 0,
        }));
      setRegionChartData(data);
    }).catch(() => {});
  }, []);

  const stats = statsApi.state.status === 'success' ? statsApi.state.data : null;
  const locationStats = locApi.state.status === 'success' ? locApi.state.data : null;

  const isLoading = statsApi.state.status === 'loading' || locApi.state.status === 'loading';

  const severityConfig = {
    critical: { color: 'var(--color-accent-rose)', icon: '🔴' },
    warning: { color: 'var(--color-accent-amber)', icon: '⚠️' },
    info: { color: 'var(--color-accent-cyan)', icon: 'ℹ️' },
    success: { color: 'var(--color-accent-emerald)', icon: '✅' },
  };

  return (
    <>
      {commandOpen && <CommandPalette onRunForecast={(s) => {}} onRunPandemic={() => {}} />}
      <div className="space-y-6">
        {/* Top Bar */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Mission Control</h1>
            <p className="text-sm text-[var(--color-text-muted)] mt-0.5">Real-time healthcare intelligence · India</p>
          </div>
          <div className="flex items-center gap-4">
            {/* IST Clock */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)]">
              <Clock className="w-3.5 h-3.5 text-[var(--color-accent-cyan)]" />
              <span className="text-sm font-mono font-medium text-[var(--color-text-primary)]">{istTime}</span>
              <span className="text-[10px] text-[var(--color-text-muted)] font-mono">IST</span>
            </div>
            {/* System Health */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)]">
              <span className="flex items-center gap-1 text-[10px] font-mono text-[var(--color-text-muted)]">
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: health.api ? 'var(--color-accent-emerald)' : 'var(--color-accent-rose)', boxShadow: health.api ? '0 0 6px var(--color-accent-emerald)' : 'none' }} />
                API
              </span>
              <span className="flex items-center gap-1 text-[10px] font-mono text-[var(--color-text-muted)]">
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: health.db ? 'var(--color-accent-emerald)' : 'var(--color-accent-rose)', boxShadow: health.db ? '0 0 6px var(--color-accent-emerald)' : 'none' }} />
                DB
              </span>
              <span className="flex items-center gap-1 text-[10px] font-mono text-[var(--color-text-muted)]">
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: health.ml ? 'var(--color-accent-emerald)' : 'var(--color-accent-rose)', boxShadow: health.ml ? '0 0 6px var(--color-accent-emerald)' : 'none' }} />
                ML
              </span>
            </div>
            {/* Command palette hint */}
            <button
              onClick={() => setCommandOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] text-[11px] text-[var(--color-text-muted)] font-mono hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-strong)] transition-all"
            >
              <Sparkles className="w-3 h-3" /> ⌘K
            </button>
          </div>
        </div>

        {/* Three-Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr_300px] gap-5">
          {/* LEFT — Live Metrics */}
          <div className="space-y-3">
            <p className="text-[10px] font-mono text-[var(--color-text-muted)] uppercase tracking-widest">Live Metrics</p>
            {isLoading ? (
              <SkeletonLoader variant="stat-card" rows={6} />
            ) : (
              <>
                <MetricCard label="Total Beds" value={stats?.beds || 0} icon={<BedDouble />} color="var(--color-accent-cyan)" sparklineData={SPARKLINE_DATA} suffix="" />
                <MetricCard label="Occupancy Rate" value={Math.round(locationStats?.beds?.avg_occupancy || 68)} icon={<Building2 />} color="var(--color-accent-amber)" delta={3.2} suffix="%" />
                <MetricCard label="Avg Mortality" value={locationStats?.mortality?.avg_death_rate ? parseFloat(locationStats.mortality.avg_death_rate.toFixed(1)) : 0} icon={<Activity />} color="var(--color-accent-rose)" suffix="%" />
                <MetricCard label="Active Outbreaks" value={6} icon={<AlertTriangle />} color="var(--color-accent-violet)" />
                <MetricCard label="Patients at Risk" value={stats?.patients ? Math.round(stats.patients * 0.12) : 0} icon={<Users />} color="var(--color-accent-amber)" delta={-5.1} deltaLabel="vs last month" />
                <MetricCard label="AI Queries Today" value={142} icon={<Sparkles />} color="var(--color-accent-emerald)" delta={22.4} deltaLabel="vs yesterday" suffix="" />
              </>
            )}
          </div>

          {/* CENTER — Map / Chart */}
          <div className="space-y-4">
            <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-[var(--color-accent-cyan)]" />
                  State-wise Bed Distribution
                </h2>
                <div className="flex items-center gap-2">
                  <StatusBadge status="live" />
                  <button className="text-[10px] font-mono text-[var(--color-text-muted)] hover:text-white transition-colors" onClick={() => navigate('/dashboard/beds')}>
                    Full Forecast →
                  </button>
                </div>
              </div>
              {regionChartData.length > 0 ? (
                <div className="h-[320px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={regionChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="barFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="var(--color-accent-cyan)" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="var(--color-accent-cyan)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" vertical={false} />
                      <XAxis dataKey="name" stroke="var(--color-text-muted)" tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} angle={-30} textAnchor="end" height={60} interval={0} />
                      <YAxis stroke="var(--color-text-muted)" tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} />
                      <Tooltip
                        cursor={{ fill: 'rgba(0,240,255,0.03)' }}
                        contentStyle={{
                          background: 'rgba(11,17,32,0.9)',
                          border: '1px solid var(--color-border-subtle)',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                        itemStyle={{ color: 'var(--color-accent-cyan)' }}
                      />
                      <Area type="monotone" dataKey="beds" name="Total Beds" stroke="var(--color-accent-cyan)" strokeWidth={2} fill="url(#barFill)" dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-[320px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">Loading state data...</div>
              )}
              {/* Choropleth legend */}
              <div className="flex items-center gap-3 mt-3 pt-3 border-t border-[var(--color-border-subtle)]">
                <span className="text-[10px] text-[var(--color-text-muted)] font-mono">Occupancy:</span>
                <div className="flex items-center gap-1">
                  {['#00ff9d', '#ffd700', '#ff8c00', '#ff3d6e'].map((c, i) => (
                    <span key={i} className="w-4 h-2 rounded" style={{ background: c }} />
                  ))}
                </div>
                <span className="text-[10px] text-[var(--color-text-muted)] font-mono">Low → High</span>
              </div>
            </div>

            {/* Quick actions */}
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => navigate('/dashboard/pandemic')}
                className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-4 text-left hover:border-[var(--color-border-strong)] transition-all group"
              >
                <p className="text-xs font-semibold text-white group-hover:text-[var(--color-accent-rose)] transition-colors">Run Pandemic Simulation</p>
                <p className="text-[10px] text-[var(--color-text-muted)] mt-1">6 ML models · 6 diseases</p>
              </button>
              <button
                onClick={() => navigate('/dashboard/ai')}
                className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-4 text-left hover:border-[var(--color-border-strong)] transition-all group"
              >
                <p className="text-xs font-semibold text-white group-hover:text-[var(--color-accent-cyan)] transition-colors">Ask AI Assistant</p>
                <p className="text-[10px] text-[var(--color-text-muted)] mt-1">RAG over 16M+ records</p>
              </button>
            </div>
          </div>

          {/* RIGHT — Intelligence Feed */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-[10px] font-mono text-[var(--color-text-muted)] uppercase tracking-widest">Intelligence Feed</p>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--color-accent-cyan)] opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--color-accent-cyan)]" />
              </span>
            </div>
            <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
              {alerts.map((alert, idx) => {
                const cfg = severityConfig[alert.severity];
                return (
                  <motion.div
                    key={alert.id}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-3"
                  >
                    <div className="flex items-start gap-2.5">
                      <span className="text-xs mt-0.5">{cfg.icon}</span>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs text-[var(--color-text-primary)] leading-relaxed">{alert.message}</p>
                        <div className="flex items-center gap-2 mt-1.5">
                          <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: `${cfg.color}15`, color: cfg.color }}>{alert.state}</span>
                          <span className="text-[10px] text-[var(--color-text-muted)]">{alert.time}</span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
            <button className="w-full text-[10px] font-mono text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors py-2 border-t border-[var(--color-border-subtle)]">
              View All Intelligence →
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

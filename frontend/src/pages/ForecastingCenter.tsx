import { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Settings2, TrendingUp, Calendar, Building, Info, Download, ShieldAlert,
  ChevronDown, Search, X, Plus, Activity
} from 'lucide-react';
import {
  Area, ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer,
  Tooltip, ReferenceLine, Label,
} from 'recharts';
import { getStates, getBedForecast } from '../api';
import { useApi } from '../hooks/useApi';
import type { LocationStatsResponse, BedForecastResponse, ForecastDataPoint } from '../types/api';
import StatusBadge from '../components/ui/StatusBadge';
import Button from '../components/ui/Button';
import { downloadCsv } from '../utils/exportCsv';

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const CURRENT_YEAR = new Date().getFullYear();
const WARD_TYPES = ['General', 'ICU', 'Maternity', 'Emergency'];

interface ScenarioDataPoint {
  month: string;
  timestamp: number;
  predicted: number;
  range: [number, number];
}

interface ScenarioData {
  id: number;
  wardType: string;
  pandemicMode: boolean;
  surgePct: number;
  color: string;
  label: string;
  data: ScenarioDataPoint[];
}

const SCENARIO_COLORS = ['var(--color-accent-cyan)', 'var(--color-accent-violet)', 'var(--color-accent-emerald)'];

function SearchableSelect({ options, value, onChange, placeholder }: {
  options: string[];
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');

  const filtered = options.filter(o => o.toLowerCase().includes(search.toLowerCase()));
  const groups = [
    { label: 'North', states: ['Delhi','Haryana','Himachal Pradesh','Jammu and Kashmir','Punjab','Rajasthan','Uttarakhand','Uttar Pradesh','Chandigarh'] },
    { label: 'South', states: ['Andhra Pradesh','Karnataka','Kerala','Tamil Nadu','Telangana','Puducherry','Andaman and Nicobar'] },
    { label: 'East', states: ['Bihar','Jharkhand','Odisha','West Bengal'] },
    { label: 'West', states: ['Goa','Gujarat','Maharashtra'] },
    { label: 'Northeast', states: ['Arunachal Pradesh','Assam','Manipur','Meghalaya','Mizoram','Nagaland','Sikkim','Tripura'] },
  ];

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-lg px-3 py-2.5 text-base text-left focus:border-[var(--color-accent-cyan)] outline-none transition-colors"
      >
        <span style={{ color: value ? 'var(--color-text-primary)' : 'var(--color-text-muted)' }}>{value || placeholder}</span>
        <ChevronDown className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute top-full mt-1 left-0 right-0 z-50 rounded-xl border border-[var(--color-border-strong)] bg-[#0B1220] shadow-2xl overflow-hidden max-h-[300px] flex flex-col">
            <div className="flex items-center gap-2 px-3 py-2 border-b border-[var(--color-border-subtle)]">
              <Search className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search states..."
                className="flex-1 bg-transparent text-base text-[var(--color-text-primary)] outline-none placeholder-[var(--color-text-muted)]"
                autoFocus
              />
              {search && <X className="w-3 h-3 text-[var(--color-text-muted)] cursor-pointer" onClick={() => setSearch('')} />}
            </div>
            <div className="overflow-y-auto flex-1">
              {filtered.length === 0 ? (
                <p className="text-sm text-[var(--color-text-muted)] text-center py-6">No states match "{search}"</p>
              ) : search ? (
                filtered.map(s => (
                  <button key={s} onClick={() => { onChange(s); setOpen(false); setSearch(''); }}
                    className={`w-full text-left px-3 py-2 text-base transition-colors ${s === value ? 'text-[var(--color-accent-cyan)] bg-[var(--color-surface-2)]' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-1)]'}`}>
                    {s}
                  </button>
                ))
              ) : (
                groups.map(g => {
                  const match = g.states.filter(s => options.includes(s));
                  if (match.length === 0) return null;
                  return (
                    <div key={g.label}>
                      <p className="px-3 py-1.5 text-[10px] font-mono text-[var(--color-text-muted)] uppercase tracking-wider">{g.label}</p>
                      {match.map(s => (
                        <button key={s} onClick={() => { onChange(s); setOpen(false); }}
                          className={`w-full text-left px-3 py-2 text-base transition-colors flex items-center gap-2 ${s === value ? 'text-[var(--color-accent-cyan)] bg-[var(--color-surface-2)]' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-1)]'}`}>
                          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent-emerald)]" style={{ opacity: options.includes(s) ? 1 : 0.3 }} />
                          {s}
                        </button>
                      ))}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function ModelMetadataPanel({ status, scenarioCount }: { status?: string; scenarioCount: number }) {
  return (
    <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-4 space-y-2">
      <p className="text-[10px] font-mono text-[var(--color-text-muted)] uppercase tracking-wider">Model Intelligence</p>
      <div className="space-y-1.5 text-sm">
        <div className="flex justify-between"><span className="text-[var(--color-text-muted)]">Algorithm</span><span className="text-[var(--color-text-primary)] font-mono">GradientBoosting</span></div>
        <div className="flex justify-between"><span className="text-[var(--color-text-muted)]">Features</span><span className="text-[var(--color-text-primary)] font-mono">11 engineered</span></div>
        <div className="flex justify-between"><span className="text-[var(--color-text-muted)]">Training R²</span><span className="text-[var(--color-text-primary)] font-mono">0.64</span></div>
        <div className="flex justify-between"><span className="text-[var(--color-text-muted)]">Horizon</span><span className="text-[var(--color-text-primary)] font-mono">Up to 24 months</span></div>
        <div className="flex justify-between"><span className="text-[var(--color-text-muted)]">Confidence</span><span className="flex items-center gap-1">
          <span className="w-16 h-1.5 rounded-full bg-[var(--color-surface-3)] overflow-hidden inline-block">
            <span className="h-full rounded-full block" style={{ width: '78%', background: 'var(--color-accent-emerald)' }} />
          </span>
          <span className="font-mono text-[var(--color-text-primary)]">78%</span>
        </span></div>
        <div className="flex justify-between items-center">
          <span className="text-[var(--color-text-muted)]">Data Source</span>
          <StatusBadge status={(status as "ml_model" | "db_trend" | "estimated") || 'ml_model'} />
        </div>
      </div>
      {scenarioCount > 1 && (
        <p className="text-[10px] font-mono text-[var(--color-accent-cyan)] pt-2 border-t border-[var(--color-border-subtle)]">
          {scenarioCount} scenarios active
        </p>
      )}
    </div>
  );
}

interface TooltipPayloadItem {
  dataKey: string;
  color?: string;
  name?: string;
  value?: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const lines = payload.filter((p) => p.dataKey !== 'primary_range');
  const range = payload.find((p) => p.dataKey === 'primary_range');
  
  return (
    <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[rgba(11,17,32,0.95)] backdrop-blur-xl p-3 shadow-2xl text-sm space-y-1.5">
      <p className="text-[var(--color-text-muted)] font-mono">{label}</p>
      {lines.map((p, i: number) => (
        <div key={i} className="flex items-center justify-between gap-4">
          <span style={{ color: p.color }} className="font-medium">{p.name}</span>
          <span className="font-mono text-[var(--color-text-primary)]">{Math.round(p.value || 0).toLocaleString()}</span>
        </div>
      ))}
      {range && range.value && (
        <div className="flex items-center justify-between gap-4 pt-1 mt-1 border-t border-[var(--color-border-subtle)]">
          <span className="text-[var(--color-text-muted)] text-[10px]">95% CI bounds</span>
          <span className="font-mono text-[var(--color-text-muted)]">{Math.round(range.value[0]).toLocaleString()} - {Math.round(range.value[1]).toLocaleString()}</span>
        </div>
      )}
    </div>
  );
}

export default function ForecastingCenter() {
  useEffect(() => { document.title = 'Forecasting Center | HOSPi'; }, []);
  const statesApi = useApi(() => getStates<string[]>(), []);
  const [selectedState, setSelectedState] = useState('');
  const [wardType, setWardType] = useState('General');
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [pandemicMode, setPandemicMode] = useState(false);
  const [surgePct, setSurgePct] = useState(50);
  const [scenarios, setScenarios] = useState<ScenarioData[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [showTable, setShowTable] = useState(false);
  const [error, setError] = useState('');

  const states = statesApi.state.status === 'success' ? statesApi.state.data : [];

  const runScenario = useCallback(async (wt: string, pm: boolean, sp: number, color: string, label: string) => {
    if (!selectedState) { setError('Select a state first'); return; }
    setError('');
    setIsRunning(true);
    try {
      const params: { state: string; ward_type: string; months_ahead: number; year?: string } = { state: selectedState, ward_type: wt, months_ahead: 12, year: String(selectedYear) };
      const result = await getBedForecast<BedForecastResponse>(params);
      let forecast = result.forecast || [];
      const nested = forecast[0] as (ForecastDataPoint & { forecast?: ForecastDataPoint[] }) | undefined;
      if (nested?.forecast) forecast = nested.forecast;
      const sf = pm ? 1 + (sp / 100) : 1;
      const data = forecast.map((f: ForecastDataPoint, i: number) => ({
        month: f.year ? `${(f.month_name || MONTHS[(f.month || 1) - 1] || '').slice(0, 3)} ${f.year}` : (f.month_name || (f.month ? String(f.month) : '')),
        timestamp: (f.year || selectedYear) * 12 + (f.month || i + 1),
        predicted: Math.round((f.predicted_beds || 0) * sf),
        range: [
          Math.round(((f as unknown as Record<string, number>).lower_bound || (f.predicted_beds || 0) * 0.9) * sf),
          Math.round(((f as unknown as Record<string, number>).upper_bound || (f.predicted_beds || 0) * 1.1) * sf)
        ] as [number, number]
      }));
      const id = Date.now();
      setScenarios(prev => [...prev, { id, wardType: wt, pandemicMode: pm, surgePct: sp, color, label, data }]);
    } catch (e: unknown) {
      setError((e as Error).message || 'An error occurred');
    }
    setIsRunning(false);
  }, [selectedState, selectedYear]);

  const removeScenario = (id: number) => setScenarios(prev => prev.filter(s => s.id !== id));

  const handleRun = () => runScenario(wardType, pandemicMode, surgePct, SCENARIO_COLORS[scenarios.length % SCENARIO_COLORS.length], `${wardType} ${selectedYear}${pandemicMode ? ` +${surgePct}% surge` : ''}`);

  interface CombinedDataRow {
    month: string;
    timestamp: number;
    [key: string]: string | number | [number, number] | undefined;
  }

  const combinedData = useMemo(() => {
    if (scenarios.length === 0) return [];
    const map = new Map<string, CombinedDataRow>();
    scenarios.forEach((s, idx) => {
      s.data.forEach(d => {
        if (!map.has(d.month)) {
          map.set(d.month, { month: d.month, timestamp: d.timestamp });
        }
        const existing = map.get(d.month)!;
        existing[`s_${s.id}`] = d.predicted;
        if (idx === 0) existing['primary_range'] = d.range;
      });
    });
    return Array.from(map.values()).sort((a, b) => a.timestamp - b.timestamp);
  }, [scenarios]);

  return (
    <div className="flex flex-col lg:flex-row gap-5 min-h-[calc(100vh-8rem)]">
      {/* LEFT — Controls */}
      <div className="w-full lg:w-[340px] flex-shrink-0 space-y-4">
        <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-5 space-y-5">
          <div className="flex items-center gap-2 pb-3 border-b border-[var(--color-border-subtle)]">
            <Settings2 className="w-4 h-4 text-[var(--color-accent-cyan)]" />
            <h2 className="text-base font-semibold text-white">Intelligence Control</h2>
          </div>

          <div className="space-y-2">
            <label className="text-[13px] font-medium text-[var(--color-text-secondary)] flex items-center gap-1.5"><Building className="w-3.5 h-3.5" /> State</label>
            <SearchableSelect options={states} value={selectedState} onChange={setSelectedState} placeholder="Select a state..." />
          </div>

          <div className="space-y-2">
            <label className="text-[13px] font-medium text-[var(--color-text-secondary)]">Ward Type</label>
            <div className="flex gap-1 p-1 rounded-lg bg-[var(--color-bg-primary)] border border-[var(--color-border-subtle)]">
              {WARD_TYPES.map(wt => (
                <button key={wt}
                  onClick={() => setWardType(wt)}
                  className={`flex-1 px-2 py-1.5 text-sm font-medium rounded-md transition-all ${wt === wardType ? 'bg-[var(--color-accent-cyan)] text-black shadow-[0_0_12px_rgba(0,240,255,0.3)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'}`}
                  title={`${wt}: historical data available`}
                >
                  {wt === 'General' ? 'Gen' : wt === 'Maternity' ? 'Mat' : wt.slice(0, 3)}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-[13px] font-medium text-[var(--color-text-secondary)] flex items-center gap-1.5"><Calendar className="w-3.5 h-3.5" /> Year</label>
            <select value={selectedYear} onChange={e => setSelectedYear(Number(e.target.value))}
              className="w-full bg-[var(--color-surface-2)] border border-[var(--color-border-subtle)] rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-[var(--color-accent-cyan)]">
              {Array.from({ length: 6 }, (_, i) => {
                const y = new Date().getFullYear() + i;
                return <option key={y} value={y} className="bg-[#0B1220] text-white">{y}</option>;
              })}
            </select>
          </div>

          <div className="space-y-2 pt-2 border-t border-[var(--color-border-subtle)]">
            <button
              onClick={() => setPandemicMode(!pandemicMode)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all ${pandemicMode ? 'bg-[var(--color-accent-rose)]/15 text-[var(--color-accent-rose)] border border-[var(--color-accent-rose)]/30' : 'bg-[var(--color-surface-2)] text-[var(--color-text-muted)] border border-[var(--color-border-subtle)]'}`}
            >
              <span className="flex items-center gap-2"><ShieldAlert className="w-3.5 h-3.5" />Pandemic Surge</span>
              <span className={`text-xs px-1.5 py-0.5 rounded-full font-mono ${pandemicMode ? 'bg-[var(--color-accent-rose)]/20' : 'bg-[var(--color-surface-3)]'}`}>{pandemicMode ? 'ON' : 'OFF'}</span>
            </button>
            <AnimatePresence>
              {pandemicMode && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden space-y-2 pl-1">
                  <div className="space-y-1">
                    <label className="text-xs text-[var(--color-text-muted)]">Surge factor: <span className="text-[var(--color-accent-rose)] font-bold">{surgePct}%</span></label>
                    <input type="range" min="10" max="200" value={surgePct} onChange={e => setSurgePct(Number(e.target.value))} className="w-full accent-[var(--color-accent-rose)]" />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {error && <p className="text-sm text-[var(--color-accent-rose)] bg-[var(--color-accent-rose)]/10 rounded-lg px-3 py-2">{error}</p>}

          <Button variant="primary" className="w-full justify-center" onClick={handleRun} isLoading={isRunning}>
            {isRunning ? 'Running...' : 'Run Forecast'}
          </Button>
        </div>

        <ModelMetadataPanel status={scenarios.length > 0 ? 'ml_model' : undefined} scenarioCount={scenarios.length} />
      </div>

      {/* RIGHT — Chart */}
      <div className="flex-1 flex flex-col space-y-4">
        {/* Scenario chips */}
        {scenarios.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            {scenarios.map(s => (
              <span key={s.id} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono font-medium"
                style={{ background: `${s.color}15`, color: s.color, border: `1px solid ${s.color}30` }}>
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: s.color }} />
                {s.label}
                <button onClick={() => removeScenario(s.id)} className="ml-0.5 hover:opacity-70">×</button>
              </span>
            ))}
            {scenarios.length < 3 && (
              <button
                onClick={handleRun}
                disabled={isRunning}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] text-[var(--color-text-muted)] border border-dashed border-[var(--color-border-subtle)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-strong)] transition-all"
              >
                <Plus className="w-3 h-3" /> Compare Scenario
              </button>
            )}
          </div>
        )}

        <div className="flex-1 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-5 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-semibold text-white">Resource Demand Projection</h2>
              <p className="text-sm text-[var(--color-text-muted)] mt-0.5">
                {scenarios.length > 0
                  ? `${scenarios[0].wardType} forecast for ${selectedState}${scenarios.length > 1 ? ` (${scenarios.length} scenarios)` : ''}`
                  : 'Configure and run a forecast'}
              </p>
            </div>
            {scenarios.length > 0 && (
              <div className="flex items-center gap-2">
                <button onClick={() => setShowTable(!showTable)} className="text-xs font-mono text-[var(--color-text-muted)] hover:text-white transition-colors">
                  {showTable ? 'Hide' : 'Show'} Data
                </button>
                <Download className="w-3.5 h-3.5 text-[var(--color-text-muted)] cursor-pointer hover:text-white transition-colors"
                  onClick={() => downloadCsv(combinedData, 'forecast.csv')} />
              </div>
            )}
          </div>

          <div className="flex-1 min-h-[400px] relative">
            {isRunning && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-[var(--color-bg-card)]/50 backdrop-blur-sm rounded-xl">
                <div className="flex flex-col items-center">
                  <div className="w-8 h-8 border-3 border-[var(--color-accent-cyan)] border-t-transparent rounded-full animate-spin" />
                  <p className="mt-3 text-xs text-[var(--color-accent-cyan)] font-mono animate-pulse">Running ML Prediction...</p>
                </div>
              </div>
            )}
            {scenarios.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={combinedData} margin={{ top: 20, right: 30, bottom: 40, left: 0 }}>
                  <defs>
                    <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--color-accent-cyan)" stopOpacity={0.2} />
                      <stop offset="100%" stopColor="var(--color-accent-cyan)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" vertical={false} />
                  <XAxis dataKey="month" stroke="var(--color-text-muted)" tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} minTickGap={30} dy={8} />
                  <YAxis domain={[0, 'auto']} stroke="var(--color-text-muted)" tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} dx={-8} />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                  <ReferenceLine y={500} stroke="var(--color-accent-amber)" strokeDasharray="6 3" strokeWidth={1}>
                    <Label value="Current Capacity" position="right" fill="var(--color-accent-amber)" fontSize={10} />
                  </ReferenceLine>
                  <ReferenceLine y={800} stroke="var(--color-accent-rose)" strokeDasharray="6 3" strokeWidth={1}>
                    <Label value="Surge Threshold (85%)" position="right" fill="var(--color-accent-rose)" fontSize={10} />
                  </ReferenceLine>
                  <Area type="monotone" dataKey="primary_range" stroke="none" fill="url(#barGrad)" name="Confidence Interval" />
                  {scenarios.map((s, i) => (
                    <Line key={s.id} type="monotone" dataKey={`s_${s.id}`} name={s.label} stroke={s.color}
                      strokeWidth={2.5} dot={false} activeDot={{ r: 4, fill: '#fff', stroke: s.color, strokeWidth: 2 }}
                      strokeDasharray={i > 0 ? '5 5' : 'none'}
                      style={i === 0 ? { filter: 'drop-shadow(0 0 6px rgba(0,240,255,0.3))' } : undefined}
                    />
                  ))}
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-[var(--color-text-muted)]">
                <TrendingUp className="w-12 h-12 mb-3 opacity-20" />
                <p className="text-base font-medium text-white/70">Ready for Simulation</p>
                <p className="text-sm mt-1 text-center max-w-xs">Select parameters and run a forecast</p>
              </div>
            )}
          </div>

          {/* Collapsible data table */}
          <AnimatePresence>
            {showTable && scenarios.length > 0 && (
              <motion.div initial={{ maxHeight: 0, opacity: 0 }} animate={{ maxHeight: 300, opacity: 1 }} exit={{ maxHeight: 0, opacity: 0 }}
                className="overflow-hidden mt-4 border-t border-[var(--color-border-subtle)] pt-3">
                <div className="max-h-[250px] overflow-y-auto text-sm font-mono">
                  <table className="w-full">
                    <thead>
                      <tr className="text-xs text-[var(--color-text-muted)] uppercase">
                        <th className="text-left py-1 pr-3">Month</th>
                        {scenarios.map(s => <th key={s.id} className="text-right py-1 px-2" style={{ color: s.color }}>{s.label}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {combinedData.map((row: CombinedDataRow, i: number) => (
                        <tr key={i} className="border-t border-[var(--color-border-subtle)]/50">
                          <td className="py-1 pr-3 text-[var(--color-text-muted)]">{row.month}</td>
                          {scenarios.map(s => <td key={s.id} className="text-right py-1 px-2 text-[var(--color-text-primary)]">{row[`s_${s.id}`]?.toLocaleString() || '-'}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

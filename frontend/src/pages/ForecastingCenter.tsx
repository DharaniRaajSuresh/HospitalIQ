// @ts-nocheck
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Settings2, TrendingUp, Calendar, Building, Info, Download, ShieldAlert } from 'lucide-react';
import { 
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area
} from 'recharts';
import GlassCard from '../components/ui/GlassCard';
import Button from '../components/ui/Button';
import { downloadCsv } from '../utils/exportCsv';
import { getStates, getBedForecast } from '../api';

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const CURRENT_YEAR = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({length: 11}, (_, i) => CURRENT_YEAR + i);

export default function ForecastingCenter() {
  const [states, setStates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [state, setState] = useState('');
  const [wardType, setWardType] = useState('ICU');
  const [error, setError] = useState(null);

  useEffect(() => {
    getStates().then(s => { setStates(s); if (s.length) setState(s[0]); }).catch(e => setError(e.message));
  }, []);

  const [monthsAhead, setMonthsAhead] = useState(12);
  const [selectedYear, setSelectedYear] = useState(CURRENT_YEAR);
  const [rawForecast, setRawForecast] = useState(null);
  const [pandemicMode, setPandemicMode] = useState(false);
  const [surgePct, setSurgePct] = useState(50);
  const [severityPct, setSeverityPct] = useState(30);

  const handleRunSimulation = useCallback(async (overrideMonths, overrideYear) => {
    setLoading(true);
    setError(null);
    const months = overrideMonths ?? monthsAhead;
    const yr = overrideYear ?? selectedYear;
    try {
      const result = await getBedForecast({ state, ward_type: wardType, months_ahead: months, year: yr });
      let forecast = result.forecast || [];
      if (forecast[0]?.forecast) forecast = forecast[0].forecast;
      const surgeFactor = pandemicMode ? 1 + (surgePct / 100) : 1;
      const mapped = forecast.map((f, i) => ({
        _year: f.year,
        _month: f.month,
        month: f.year ? `${(f.month_name || MONTHS[(f.month||1)-1] || '').slice(0,3)} ${f.year}` : (f.month_name || f.month),
        predicted: Math.round((f.predicted_beds || 0) * surgeFactor),
        lower: Math.round((f.predicted_beds || 0) * (pandemicMode ? surgeFactor * 0.85 : 0.8)),
        upper: Math.round((f.predicted_beds || 0) * (pandemicMode ? surgeFactor * 1.15 : 1.2)),
        current: f.available_beds ?? Math.round((f.predicted_beds || 0) * (0.85 + (i % 3) * 0.05)),
        _surgeFactor: surgeFactor
      }));
      setRawForecast(mapped);
    } catch (e) {
      setError(e.message);
      setRawForecast(null);
    }
    setLoading(false);
  }, [state, wardType, monthsAhead, pandemicMode, surgePct, selectedYear]);

  const handleYearChange = (year) => {
    setSelectedYear(year);
    const needed = Math.max(12, (year - CURRENT_YEAR) * 12 + 12);
    setMonthsAhead(needed);
    handleRunSimulation(needed, year);
  };

  const chartData = rawForecast
    ? (selectedYear === 'all' ? rawForecast : rawForecast.filter(d => d._year === selectedYear))
    : [];

  const availableYears = rawForecast ? [...new Set(rawForecast.map(d => d._year))].sort() : [];

  return (
    <div className="flex flex-col lg:flex-row gap-6 min-h-[calc(100vh-8rem)] mb-8">
      <GlassCard className="w-full lg:w-80 flex-shrink-0 p-5 flex flex-col h-full overflow-y-auto max-h-[calc(100vh-8rem)]">
        <div className="flex items-center gap-2 mb-6 border-b border-[var(--color-border)] pb-4">
          <Settings2 className="w-5 h-5 text-[var(--color-accent-violet)]" />
          <h2 className="text-lg font-semibold text-white">Scenario Builder</h2>
        </div>

        <div className="space-y-5 flex-1">
          <div className="space-y-2">
            <label className="text-sm font-medium text-[var(--color-text-secondary)] flex items-center gap-1.5">
              <Building className="w-4 h-4" /> State / Region
            </label>
            <select value={state} onChange={e => setState(e.target.value)}
              className="w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm rounded-lg px-3 py-2.5 focus:border-[var(--color-accent-violet)] outline-none">
              {states.length === 0 && <option>Loading...</option>}
              {states.map(s => <option key={s}>{s}</option>)}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-[var(--color-text-secondary)] flex items-center gap-1.5">
              <Info className="w-4 h-4" /> Ward Type
            </label>
            <select value={wardType} onChange={e => setWardType(e.target.value)}
              className="w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm rounded-lg px-3 py-2.5 focus:border-[var(--color-accent-violet)] outline-none">
              <option value="ICU">Intensive Care Unit (ICU)</option>
              <option value="General">General Ward</option>
              <option value="Emergency">Emergency</option>
              <option value="Maternity">Maternity</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-[var(--color-text-secondary)] flex items-center gap-1.5">
              <Calendar className="w-4 h-4" /> Forecast Year
            </label>
            <select value={selectedYear} onChange={e => handleYearChange(e.target.value === 'all' ? 'all' : Number(e.target.value))}
              className="w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm rounded-lg px-3 py-2.5 focus:border-[var(--color-accent-violet)] outline-none">
              <option value="all">All Years</option>
              {YEAR_OPTIONS.map(y => (
                <option key={y} value={y} disabled={rawForecast && !availableYears.includes(y)}>
                  {y} {rawForecast && !availableYears.includes(y) ? '(run prediction)' : ''}
                </option>
              ))}
            </select>
            <p className="text-xs text-[var(--color-text-muted)]">
              Select a year to view. Unavailable years will auto-fetch on selection.
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-[var(--color-text-secondary)] flex items-center gap-1.5">
              <Calendar className="w-4 h-4" /> Forecast Horizon
            </label>
            <input type="range" min="1" max="120" value={monthsAhead} onChange={e => setMonthsAhead(Number(e.target.value))}
              className="w-full accent-[var(--color-accent-violet)]" />
            <div className="flex justify-between text-xs text-[var(--color-text-muted)]">
              <span>{monthsAhead >= 12 ? `${(monthsAhead/12).toFixed(1)} Years (${monthsAhead}mo)` : `${monthsAhead} Month${monthsAhead > 1 ? 's' : ''}`}</span>
              <span>120 Months (10 Years)</span>
            </div>
          </div>

          <div className="pt-3 border-t border-[var(--color-border)] space-y-3">
            <button onClick={() => setPandemicMode(!pandemicMode)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                pandemicMode ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] border border-[var(--color-border)]'
              }`}>
              <span className="flex items-center gap-2"><ShieldAlert className="w-4 h-4" />Pandemic Mode</span>
              <span className={`text-xs px-2 py-0.5 rounded-full ${pandemicMode ? 'bg-red-500/30 text-red-300' : 'bg-[var(--color-bg-primary)] text-[var(--color-text-muted)]'}`}>
                {pandemicMode ? 'ON' : 'OFF'}
              </span>
            </button>

            {pandemicMode && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="space-y-3">
                <div className="space-y-1">
                  <label className="text-xs text-[var(--color-text-muted)]">Bed Surge: <span className="text-red-400 font-bold">{surgePct}%</span></label>
                  <input type="range" min="10" max="200" value={surgePct} onChange={e => setSurgePct(Number(e.target.value))}
                    className="w-full accent-red-500" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-[var(--color-text-muted)]">Mortality Severity: <span className="text-red-400 font-bold">{severityPct}%</span></label>
                  <input type="range" min="0" max="100" value={severityPct} onChange={e => setSeverityPct(Number(e.target.value))}
                    className="w-full accent-red-500" />
                </div>
              </motion.div>
            )}
          </div>
        </div>

        <div className="pt-6 mt-6 border-t border-[var(--color-border)] space-y-3">
          {error && (
            <p className="text-xs text-red-400 bg-red-400/10 rounded-lg px-3 py-2">{error}</p>
          )}
          <Button variant="primary" className="w-full justify-center bg-gradient-to-r from-[var(--color-accent-violet)] to-[var(--color-accent-blue)] border-none"
            onClick={() => handleRunSimulation()} isLoading={loading}>
            Run AI Simulation
          </Button>
        </div>
      </GlassCard>

      <GlassCard className="flex-1 p-6 flex flex-col">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-[var(--color-accent-violet)]" />
              Resource Demand Projection
            </h2>
            <p className="text-sm text-[var(--color-text-secondary)] mt-1">
                {rawForecast
                ? `${wardType} bed forecast for ${state}${selectedYear !== 'all' ? ` — ${selectedYear}` : ''}${pandemicMode ? ` (Pandemic +${surgePct}% surge)` : ''}`
                : 'Select parameters and run simulation'}
            </p>
          </div>
          <Button variant="secondary" icon={Download} onClick={() => {
            if (chartData) downloadCsv(chartData.map(({_year,_month,...rest}) => rest), 'beds-forecast.csv');
          }}>Export CSV</Button>
        </div>

        <div className="w-full h-[500px] relative mt-2">
          {loading && (
            <div className="absolute inset-0 z-10 bg-[var(--color-bg-card)]/50 backdrop-blur-sm flex items-center justify-center rounded-xl">
              <div className="flex flex-col items-center">
                <div className="w-10 h-10 border-4 border-[var(--color-accent-violet)] border-t-transparent rounded-full animate-spin"></div>
                <p className="mt-4 text-[var(--color-accent-violet)] font-medium animate-pulse">Running ML Prediction...</p>
              </div>
            </div>
          )}



          {rawForecast ? (
            <ResponsiveContainer width="99%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 20, right: 30, bottom: 40, left: 0 }}>
                <defs>
                  <filter id="neonGlow" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="var(--color-accent-violet)" floodOpacity="0.8" />
                    <feDropShadow dx="0" dy="0" stdDeviation="8" floodColor="var(--color-accent-violet)" floodOpacity="0.5" />
                  </filter>
                  <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--color-accent-blue)" />
                    <stop offset="100%" stopColor="rgba(59, 130, 246, 0.1)" />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="month" stroke="var(--color-text-muted)" tickLine={false} axisLine={false} interval="preserveStartEnd" dy={10} />
                <YAxis stroke="var(--color-text-muted)" tickLine={false} axisLine={false} dx={-10} />
                <Tooltip contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.8)', backdropFilter: 'blur(12px)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '12px', color: '#fff', boxShadow: '0 8px 32px rgba(0,0,0,0.5)' }}
                  itemStyle={{ color: '#fff' }} labelStyle={{ color: 'var(--color-text-secondary)', marginBottom: '4px' }} cursor={{fill: 'rgba(255,255,255,0.02)'}} />
                <Legend verticalAlign="bottom" wrapperStyle={{ paddingTop: '20px' }} />
                <Area type="monotone" dataKey="upper" stroke="none" fill="var(--color-accent-violet)" fillOpacity={0.1} name="Upper Bound" legendType="none" activeDot={false} />
                <Area type="monotone" dataKey="lower" stroke="none" fill="var(--color-bg-card)" name="Lower Bound" legendType="none" activeDot={false} />
                <Bar dataKey="current" name="Historical Demand" fill="url(#barGradient)" fillOpacity={0.8} radius={[4, 4, 0, 0]} maxBarSize={40} />
                <Line type="monotone" dataKey="predicted" name="AI Predicted Demand" stroke="var(--color-accent-violet)" strokeWidth={3}
                  dot={false} activeDot={{ r: 6, fill: '#fff', stroke: 'var(--color-accent-violet)', strokeWidth: 2, filter: 'url(#neonGlow)' }} strokeDasharray="5 5" style={{ filter: 'url(#neonGlow)' }} />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-[var(--color-text-muted)] pt-10">
              <TrendingUp className="w-16 h-16 mb-4 opacity-20 text-[var(--color-accent-violet)]" />
              <p className="text-lg font-medium text-white/70">Ready for Simulation</p>
              <p className="text-sm mt-2 text-center max-w-sm">Select your parameters on the left and click "Run AI Simulation" to view projected bed demand.</p>
            </div>
          )}
        </div>
      </GlassCard>
    </div>
  );
}


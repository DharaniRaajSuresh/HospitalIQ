// @ts-nocheck
import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { BedDouble, Activity, Building, TrendingUp, Calendar, Download, ShieldAlert, Info, Settings2 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import GlassCard from '../components/ui/GlassCard';
import KPICard from '../components/ui/KPICard';
import Button from '../components/ui/Button';
import { downloadCsv } from '../utils/exportCsv';
import { getStates, getPandemicScenario } from '../api';

const PANDEMIC_DISEASES = [
  { api: 'COVID-19',  name: 'COVID-19',             type: 'Coronavirus',            fatality: '1-5%',     r0: '3.2', dataType: 'Real' },
  { api: 'Ebola',     name: 'Ebola',                type: 'Viral Hemorrhagic Fever', fatality: '50-90%',   r0: '2.0', dataType: 'WHO-model' },
  { api: 'H1N1',      name: 'H1N1 Influenza',       type: 'Pandemic Influenza',      fatality: '0.1-2%',   r0: '1.5', dataType: 'WHO-model' },
  { api: 'SARS',      name: 'SARS',                 type: 'Coronavirus',             fatality: '10-15%',   r0: '3.0', dataType: 'WHO-model' },
  { api: 'Nipah',     name: 'Nipah',                type: 'Henipavirus',             fatality: '40-75%',   r0: '1.2', dataType: 'WHO-model' },
  { api: 'Marburg',   name: 'Marburg',              type: 'Viral Hemorrhagic Fever', fatality: '24-88%',   r0: '1.8', dataType: 'WHO-model' },
];

function TolerabilityGauge({ riskScore, riskLevel, verdict }) {
  const rs = riskScore ?? 0;
  const rl = riskLevel ?? 'unknown';
  const getColor = () => {
    if (rs < 30) return '#22c55e';
    if (rs < 55) return '#eab308';
    if (rs < 80) return '#f97316';
    return '#ef4444';
  };
  const getBg = () => {
    if (rs < 30) return 'bg-emerald-400/10 text-emerald-400';
    if (rs < 55) return 'bg-yellow-400/10 text-yellow-400';
    if (rs < 80) return 'bg-orange-400/10 text-orange-400';
    return 'bg-red-400/10 text-red-400';
  };
  const r = 60, circ = 2 * Math.PI * r;
  const offset = circ - (rs / 100) * circ;
  return (
    <div className="flex flex-col items-center py-2">
      <svg width="160" height="160" viewBox="0 0 160 160">
        <circle cx="80" cy="80" r={r} fill="none" stroke="var(--color-border)" strokeWidth="12" />
        <circle cx="80" cy="80" r={r} fill="none" stroke={getColor()} strokeWidth="12"
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
          transform="rotate(-90 80 80)" style={{ transition: 'stroke-dashoffset 0.8s ease' }} />
        <text x="80" y="68" textAnchor="middle" fill="white" fontSize="28" fontWeight="bold">{rs}</text>
        <text x="80" y="92" textAnchor="middle" fill="var(--color-text-muted)" fontSize="11">Risk Score</text>
      </svg>
      <span className={`mt-2 text-xs font-bold px-3 py-1 rounded-full ${getBg()}`}>{rl.toUpperCase()}</span>
      <p className="text-sm text-[var(--color-text-primary)] mt-2 text-center font-medium leading-snug">{verdict ?? 'Unknown'}</p>
    </div>
  );
}

function CapacityBar({ label, current, projected, unit, color }) {
  const c = current ?? 0;
  const p = projected ?? 0;
  const maxVal = Math.max(c, p, 1);
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-sm">
        <span className="text-[var(--color-text-secondary)]">{label}</span>
        <span className="text-white font-medium">{p.toLocaleString()}{unit} <span className="text-xs text-[var(--color-text-muted)]">(current: {c.toLocaleString()}{unit})</span></span>
      </div>
      <div className="flex gap-1 h-4 rounded-full overflow-hidden bg-[var(--color-bg-primary)]">
        {p > c ? (
          <>
            <div style={{ width: `${(c / maxVal) * 100}%` }} className="bg-[var(--color-border)] h-full transition-all" />
            <div style={{ width: `${((p - c) / maxVal) * 100}%` }} className={`${color} h-full transition-all opacity-80`} />
          </>
        ) : (
          <>
            <div style={{ width: `${(p / maxVal) * 100}%` }} className={`${color} h-full transition-all opacity-80`} />
            <div style={{ width: `${((c - p) / maxVal) * 100}%` }} className="bg-[var(--color-border)] h-full transition-all" />
          </>
        )}
      </div>
      <div className="flex justify-between text-xs text-[var(--color-text-muted)]">
        <span>Current: {c.toLocaleString()}{unit}</span>
        <span>Projected: {p.toLocaleString()}{unit}</span>
      </div>
    </div>
  );
}

export default function PandemicScenario() {
  const [states, setStates] = useState([]);
  const [state, setState] = useState('');
  const [disease, setDisease] = useState(PANDEMIC_DISEASES[0]);
  const [year, setYear] = useState(2025);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  useEffect(() => {
    getStates().then(s => { setStates(s); if (s.length) setState(s[0]); }).catch(e => setError(e.message));
  }, []);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({ disease: disease.api, state, year });
    try {
      setResult(await getPandemicScenario(disease.api, state, year));
    } catch (e) {
      setError(e.message);
      setResult(null);
    }
    setLoading(false);
  };

  const chartData = (result?.monthly_breakdown || []).filter(m => m.year === year);
  const isRealData = disease.dataType === 'Real';
  const tol = result?.tolerability || {};
  const safe = (v, d) => v ?? d ?? '—';

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <ShieldAlert className="w-7 h-7 text-[var(--color-accent-rose)]" />
            Pandemic Scenario Simulator
          </h1>
          <p className="text-[var(--color-text-secondary)] mt-1">
            Project outbreak impact on healthcare capacity up to 2040.
          </p>
        </div>
        {result && (
          <Button variant="ghost" icon={Download} onClick={() => downloadCsv(chartData, 'pandemic-scenario.csv')}>
            Export CSV
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <GlassCard className="p-5 space-y-4 lg:col-span-1">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2 border-b border-[var(--color-border)] pb-3">
            <Settings2 className="w-5 h-5 text-[var(--color-accent-rose)]" />
            Outbreak Parameters
          </h2>

          <div className="space-y-2">
            <label className="text-sm font-medium text-[var(--color-text-secondary)] flex items-center gap-1.5">
               <Activity className="w-4 h-4" /> Disease
            </label>
            <select value={disease.api} onChange={e => setDisease(PANDEMIC_DISEASES.find(d => d.api === e.target.value))}
              className="w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm rounded-lg px-3 py-2.5 focus:border-[var(--color-accent-rose)] focus:ring-1 focus:ring-[var(--color-accent-rose)] outline-none">
              {PANDEMIC_DISEASES.map(d => <option key={d.api} value={d.api}>{d.name} ({d.dataType})</option>)}
            </select>
            <div className="flex gap-3 text-xs text-[var(--color-text-muted)] px-1">
              <span>CFR: <span className="text-[var(--color-accent-rose)] font-medium">{disease.fatality}</span></span>
              <span>R₀: <span className="text-[var(--color-accent-cyan)] font-medium">{disease.r0}</span></span>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-[var(--color-text-secondary)]"><Building className="w-4 h-4 inline mr-1" />State / Region</label>
            <select value={state} onChange={e => setState(e.target.value)}
              className="w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm rounded-lg px-3 py-2.5 focus:border-[var(--color-accent-rose)] focus:ring-1 focus:ring-[var(--color-accent-rose)] outline-none">
              {states.length === 0 && <option>Loading...</option>}
              {states.map(s => <option key={s}>{s}</option>)}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-[var(--color-text-secondary)]">
              <Calendar className="w-4 h-4 inline mr-1" />Projection Year: <span className="text-[var(--color-accent-cyan)] font-bold">{year}</span>
            </label>
            <input type="range" min="2020" max="2040" value={year} onChange={e => setYear(Number(e.target.value))}
              className="w-full accent-[var(--color-accent-cyan)]" />
            <div className="flex justify-between text-xs text-[var(--color-text-muted)]"><span>2020</span><span>2040</span></div>
          </div>


          {error && <p className="text-xs text-red-400 bg-red-400/10 rounded-lg px-3 py-2">{error}</p>}

          <Button variant="primary" className="w-full justify-center bg-gradient-to-r from-[var(--color-accent-rose)] to-[var(--color-accent-violet)] border-none"
            onClick={handleRun} isLoading={loading}>
            {loading ? 'Simulating...' : `Run ${year} Scenario`}
          </Button>
        </GlassCard>

        <div className="lg:col-span-3 space-y-6">
          {!result && !loading && (
            <GlassCard className="p-16 flex items-center justify-center">
              <div className="text-center">
                <ShieldAlert className="w-16 h-16 text-[var(--color-text-muted)] mx-auto mb-4 opacity-30" />
                <p className="text-lg text-[var(--color-text-muted)]">Select disease, state, year and click <span className="text-[var(--color-accent-rose)] font-semibold">Run Scenario</span>.</p>
              </div>
            </GlassCard>
          )}

          {loading && (
            <GlassCard className="p-16 flex items-center justify-center">
              <div className="flex flex-col items-center">
                <div className="w-12 h-12 border-4 border-[var(--color-accent-rose)] border-t-transparent rounded-full animate-spin"></div>
                <p className="mt-4 text-[var(--color-accent-rose)] font-medium animate-pulse">Analyzing outbreak data...</p>
              </div>
            </GlassCard>
          )}

          {result && (
            <>
              <div className="flex items-center gap-3 mb-2 flex-wrap">
                <span className="text-lg font-bold text-white">{disease.name}</span>
                <span className={`text-xs px-2 py-1 rounded-full font-medium ${isRealData ? 'bg-emerald-400/20 text-emerald-400' : 'bg-violet-400/20 text-violet-400'}`}>
                  {isRealData ? 'Real District Data' : 'WHO-Parameterized'}
                </span>
                <span className="text-xs px-2 py-1 rounded-full bg-cyan-400/10 text-cyan-400 font-medium">
                  {result.state} &middot; {result.projection_year}
                </span>
                <span className="text-xs text-[var(--color-text-muted)]">
                  R0={result.outbreak_summary.avg_reproduction_rate} &middot; Base CFR={result.outbreak_summary.avg_case_fatality_rate}%
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <KPICard label="Total Confirmed Cases" value={result.outbreak_summary?.total_confirmed_cases ?? '—'} icon={Activity} color="rose" trend={result.state} />
                <KPICard label="Total Deaths" value={result.outbreak_summary?.total_deaths ?? '—'} icon={Activity} color="rose" trend={`Base CFR: ${result.outbreak_summary?.avg_case_fatality_rate ?? '—'}%`} />
                <KPICard label="Bed Demand (peak)" value={result.projected_impact?.projected_bed_demand ?? '—'} icon={BedDouble} color="violet" trend={`Year: ${result.projection_year ?? '—'}`} />
                <KPICard label="Bed Occupancy (peak)" value={result.projected_impact?.bed_occupancy != null ? result.projected_impact.bed_occupancy + '%' : '—'} icon={Building} color={(result.projected_impact?.bed_occupancy ?? 0) > 85 ? 'rose' : 'emerald'} trend={`${(result.projected_impact?.bed_shortage ?? 0) > 0 ? (result.projected_impact?.bed_shortage ?? 0) + ' beds short' : 'adequate capacity'}`} />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <GlassCard className="p-5 lg:col-span-1">
                  <h2 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-[var(--color-accent-amber)]" />
                    Tolerability Assessment
                  </h2>
                  <TolerabilityGauge riskScore={tol.risk_score} riskLevel={tol.risk_level} verdict={tol.verdict} />
                  <div className="mt-4 space-y-2 border-t border-[var(--color-border)] pt-4">
                    <div className="flex justify-between text-sm">
                      <span className="text-[var(--color-text-secondary)]">Bed Occupancy Risk</span>
                      <span className="text-white font-medium">{safe(tol.bed_occupancy_risk)}%</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[var(--color-text-secondary)]">Fatality Risk</span>
                      <span className="text-white font-medium">{safe(tol.fatality_risk)}%</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[var(--color-text-secondary)]">ICU Capacity Risk</span>
                      <span className="text-white font-medium">{safe(tol.icu_capacity_risk)}%</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[var(--color-text-secondary)]">Bed Demand Risk</span>
                      <span className="text-white font-medium">{safe(tol.bed_demand_risk)}%</span>
                    </div>
                  </div>
                </GlassCard>

                <GlassCard className="p-5 lg:col-span-2">
                  <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
                    <Building className="w-4 h-4 text-[var(--color-accent-cyan)]" />
                    Current vs Projected Capacity — {result.state} ({result.projection_year})
                  </h2>
                  <div className="space-y-5">
                    <CapacityBar label="Bed Demand" current={result.current_capacity?.total_beds} projected={result.projected_impact?.projected_bed_demand} unit=" beds" color="bg-violet-500" />
                    <CapacityBar label="ICU Demand" current={result.current_capacity?.icu_capacity} projected={result.projected_impact?.projected_icu_demand} unit=" beds" color="bg-rose-500" />
                    <CapacityBar label="Fatality Rate" current={result.outbreak_summary?.avg_case_fatality_rate} projected={result.projected_impact?.projected_cfr} unit="%" color="bg-red-500" />
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-sm">
                        <span className="text-[var(--color-text-secondary)]">Available Beds</span>
                        <span className="text-white font-medium">{safe(result.projected_impact?.available_beds)?.toLocaleString()} <span className="text-xs text-[var(--color-text-muted)]">(current: {safe(result.current_capacity?.available_beds)?.toLocaleString()})</span></span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-[var(--color-text-secondary)]">Bed Shortage</span>
                        <span className={(result.projected_impact?.bed_shortage ?? 0) > 0 ? 'text-red-400 font-bold' : 'text-emerald-400 font-medium'}>
                          {(result.projected_impact?.bed_shortage ?? 0) > 0 ? `${(result.projected_impact?.bed_shortage ?? 0).toLocaleString()} beds` : 'None'}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-[var(--color-text-secondary)]">ICU Shortage</span>
                        <span className={(result.projected_impact?.icu_shortage ?? 0) > 0 ? 'text-red-400 font-bold' : 'text-emerald-400 font-medium'}>
                          {(result.projected_impact?.icu_shortage ?? 0) > 0 ? `${(result.projected_impact?.icu_shortage ?? 0).toLocaleString()} beds` : 'None'}
                        </span>
                      </div>
                    </div>
                  </div>
                </GlassCard>
              </div>

              <GlassCard className="p-6">
                <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-[var(--color-accent-rose)]" />
                  Monthly Cases in {result.projection_year}: {disease.name} in {result.state}
                </h2>
                <div className="h-80">
                  <ResponsiveContainer width="99%" height="100%">
                    <BarChart data={chartData} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                      <XAxis dataKey="month" stroke="var(--color-text-muted)" tickLine={false} axisLine={false} interval="preserveStartEnd" angle={-20} textAnchor="end" height={60} />
                      <YAxis stroke="var(--color-text-muted)" tickLine={false} axisLine={false} tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
                      <Tooltip contentStyle={{ backgroundColor: 'var(--color-bg-card)', borderColor: 'var(--color-border)', borderRadius: '8px', color: '#fff' }} />
                      <Legend wrapperStyle={{ paddingTop: '16px' }} />
                      <Bar dataKey="confirmed_cases" name="Confirmed Cases" fill="var(--color-accent-rose)" radius={[4,4,0,0]} maxBarSize={30} />
                      <Bar dataKey="deaths" name="Deaths" fill="var(--color-accent-violet)" radius={[4,4,0,0]} maxBarSize={30} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </GlassCard>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <GlassCard className="p-6">
                  <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Info className="w-5 h-5 text-[var(--color-accent-amber)]" />
                    Recommendations for {result.projection_year}
                  </h2>
                  <div className="space-y-3">
                    {result.recommendations.map((rec, i) => (
                      <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}
                        className={`p-3 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-sm ${rec.startsWith('OVERWHELMING') ? 'text-red-400 font-bold' : rec.startsWith('CRITICAL') ? 'text-orange-400 font-bold' : 'text-[var(--color-text-primary)]'}`}>
                        {rec}
                      </motion.div>
                    ))}
                  </div>
                </GlassCard>

                <GlassCard className="p-6">
                  <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Building className="w-5 h-5 text-[var(--color-accent-rose)]" />
                    Hospitals at Risk
                  </h2>
                  {result.hospitals_at_risk.length > 0 ? (
                    <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                      {result.hospitals_at_risk.map((h, i) => (
                        <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)]">
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-white truncate">{h.name}</p>
                            <p className="text-xs text-[var(--color-text-muted)]">{h.district} &middot; {h.type} &middot; {h.beds} beds</p>
                          </div>
                          <div className="flex gap-2 flex-shrink-0 ml-2">
                            <span className="text-xs px-2 py-1 rounded bg-red-400/10 text-red-400 font-medium">{h.icu_beds} ICU</span>
                            <span className="text-xs px-2 py-1 rounded bg-violet-400/10 text-violet-400 font-medium">{h.specialists} specialists</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-[var(--color-text-muted)]">No hospitals flagged at risk for this scenario.</p>
                  )}
                </GlassCard>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}


import { useState, useEffect, useRef } from 'react';
import { ShieldAlert, Download, ChevronRight, Info } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip, ReferenceLine } from 'recharts';
import { getStates, getPandemicScenario } from '../api';
import { useApi } from '../hooks/useApi';
import { PandemicScenarioResponse, HospitalRiskItem } from '../types/api';
import StatusBadge from '../components/ui/StatusBadge';
import Button from '../components/ui/Button';
import PipelineVisualizer from '../components/ui/PipelineVisualizer';
import { downloadCsv } from '../utils/exportCsv';

const DISEASES = [
  { api: 'COVID-19', name: 'COVID-19', type: 'Coronavirus', fatality: '1-5%', r0: '3.2', color: '#f97316' },
  { api: 'Ebola', name: 'Ebola', type: 'Viral Hemorrhagic Fever', fatality: '50-90%', r0: '2.0', color: '#ef4444' },
  { api: 'H1N1', name: 'H1N1 Influenza', type: 'Pandemic Influenza', fatality: '0.1-2%', r0: '1.5', color: '#22c55e' },
  { api: 'SARS', name: 'SARS', type: 'Coronavirus', fatality: '10-15%', r0: '3.0', color: '#eab308' },
  { api: 'Nipah', name: 'Nipah', type: 'Henipavirus', fatality: '40-75%', r0: '1.2', color: '#a855f7' },
  { api: 'Marburg', name: 'Marburg', type: 'Viral Hemorrhagic Fever', fatality: '24-88%', r0: '1.8', color: '#ec4899' },
];

const PIPELINE_STEPS = [
  { label: 'Fetching outbreak data...', status: 'pending' as const },
  { label: 'Running BedPredictor...', status: 'pending' as const },
  { label: 'Running MortalityPredictor...', status: 'pending' as const },
  { label: 'Running ForecastPredictor...', status: 'pending' as const },
  { label: 'Computing risk score...', status: 'pending' as const },
  { label: 'Generating recommendations...', status: 'pending' as const },
];

function RiskGauge({ score, level, verdict }: { score: number; level: string; verdict: string }) {
  const getColor = () => {
    if (score < 30) return 'var(--color-accent-emerald)';
    if (score < 55) return 'var(--color-accent-amber)';
    if (score < 80) return '#f97316';
    return 'var(--color-accent-rose)';
  };
  const color = getColor();
  const r = 70;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;

  return (
    <div className="flex flex-col items-center">
      <svg width="180" height="180" viewBox="0 0 180 180">
        <circle cx="90" cy="90" r={r} fill="none" stroke="var(--color-surface-3)" strokeWidth="14" />
        <circle cx="90" cy="90" r={r} fill="none" stroke={color} strokeWidth="14"
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
          transform="rotate(-90 90 90)" style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.34, 1.56, 0.64, 1)' }} />
        <text x="90" y="76" textAnchor="middle" fill="white" fontSize="32" fontWeight="bold" fontFamily="var(--font-mono)">{score}</text>
        <text x="90" y="98" textAnchor="middle" fill="var(--color-text-muted)" fontSize="13">Risk Score</text>
        <text x="90" y="118" textAnchor="middle" fill={color} fontSize="12" fontWeight="bold" fontFamily="var(--font-mono)">{level}</text>
      </svg>
      <p className="text-sm text-[var(--color-text-primary)] mt-2 text-center leading-relaxed max-w-[200px]">{verdict}</p>
    </div>
  );
}

function SatelliteMetric({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-[22px] font-bold font-mono" style={{ color }}>{typeof value === 'number' ? value.toLocaleString() : value}</span>
      <span className="text-[11px] font-mono text-[var(--color-text-muted)] uppercase tracking-wider">{label}</span>
    </div>
  );
}

export default function PandemicScenario() {
  useEffect(() => { document.title = 'Pandemic Scenario | HOSPi'; }, []);

  const statesApi = useApi(() => getStates<string[]>(), []);
  const [step, setStep] = useState(0);
  const [disease, setDisease] = useState(DISEASES[0]);
  const [selectedState, setSelectedState] = useState('');
  const [year, setYear] = useState(2025);
  const [result, setResult] = useState<PandemicScenarioResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showCases, setShowCases] = useState(true);
  const [expandedHospital, setExpandedHospital] = useState<number | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const states = statesApi.state.status === 'success' ? statesApi.state.data : [];

  useEffect(() => {
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, []);

  const handleRun = async () => {
    if (!selectedState) { setError('Select a state first'); return; }
    setError('');
    setLoading(true);
    setStep(0);
    setResult(null);

    // Animate pipeline
    intervalRef.current = setInterval(() => {
      setStep(prev => {
        if (prev >= 5) { clearInterval(intervalRef.current!); return prev; }
        return prev + 1;
      });
    }, 400);

    try {
      const data = await getPandemicScenario<PandemicScenarioResponse>(disease.api, selectedState, String(year));
      setResult(data);
      setStep(6);
    } catch (e: any) {
      setError(e.message);
    }
    clearInterval(intervalRef.current);
    setLoading(false);
  };

  const pipelineSteps = PIPELINE_STEPS.map((s, i) => ({
    ...s,
    status: i < step ? 'done' as const : i === step && step < 6 && loading ? 'running' as const : s.status,
  }));

  const chartData = (result?.monthly_breakdown || []).filter(m => m.year === year);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-[var(--color-accent-rose)]" />
            Pandemic Scenario Simulator
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-0.5">6-ML Model Orchestration · Disease Outbreak Intelligence</p>
        </div>
        {result && (
          <Button variant="ghost" icon={Download} onClick={() => downloadCsv(chartData, 'pandemic.csv')}>Export</Button>
        )}
      </div>

      {/* Step 1: Disease + State selector */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-4 h-full">
            <p className="text-xs font-mono text-[var(--color-text-muted)] uppercase tracking-wider mb-3">Step 1: Select Disease</p>
            <div className="grid grid-cols-2 gap-2">
              {DISEASES.map(d => (
                <button key={d.api} onClick={() => setDisease(d)}
                  className={`p-3 rounded-xl border text-left transition-all ${d.api === disease.api ? 'border-[var(--color-accent-cyan)] bg-[var(--color-surface-2)]' : 'border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] hover:border-[var(--color-border-strong)]'}`}
                  style={{ transform: d.api === disease.api ? 'scale(1.02)' : 'scale(1)', transition: 'transform 200ms cubic-bezier(0.34,1.56,0.64,1)' }}
                >
                  <p className="text-sm font-semibold text-white">{d.name}</p>
                  <p className="text-[11px] text-[var(--color-text-muted)] mt-0.5 font-mono">CFR {d.fatality} · R₀ {d.r0}</p>
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-4 space-y-3 h-full flex flex-col justify-between">
            <p className="text-xs font-mono text-[var(--color-text-muted)] uppercase tracking-wider">Step 2: Parameters</p>
            <div className="space-y-2">
              <label className="text-[13px] text-[var(--color-text-secondary)]">State</label>
              <select value={selectedState} onChange={e => setSelectedState(e.target.value)}
                className="w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] text-base rounded-lg px-3 py-2.5 text-[var(--color-text-primary)] focus:border-[var(--color-accent-cyan)] outline-none">
                <option value="">Select...</option>
                {states.map(s => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-[13px] text-[var(--color-text-secondary)]">Year: <span className="text-[var(--color-accent-cyan)] font-mono">{year}</span></label>
              <input type="range" min="2020" max="2040" value={year} onChange={e => setYear(Number(e.target.value))} className="w-full accent-[var(--color-accent-cyan)]" />
              <div className="flex justify-between text-xs text-[var(--color-text-muted)] font-mono"><span>2020</span><span>2040</span></div>
            </div>
            {error && <p className="text-sm text-[var(--color-accent-rose)] bg-[var(--color-accent-rose)]/10 rounded-lg px-3 py-2">{error}</p>}
            <Button variant="primary" className="w-full justify-center" onClick={handleRun} isLoading={loading}>
              {loading ? 'Simulating...' : `Run ${year} Scenario`}
            </Button>

            {/* Model metadata */}
            <div className="pt-3 border-t border-[var(--color-border-subtle)] space-y-1.5 text-xs font-mono">
              <div className="flex justify-between text-[var(--color-text-muted)]"><span>Disease</span><span className="text-[var(--color-text-primary)]">{disease.name}</span></div>
              <div className="flex justify-between text-[var(--color-text-muted)]"><span>CFR</span><span className="text-[var(--color-accent-rose)]">{disease.fatality}</span></div>
              <div className="flex justify-between text-[var(--color-text-muted)]"><span>R₀</span><span className="text-[var(--color-accent-cyan)]">{disease.r0}</span></div>
              <div className="flex justify-between text-[var(--color-text-muted)]"><span>Models</span><StatusBadge status="ml_model" label="6 ML Ensemble" /></div>
            </div>
          </div>
      </div>

      {/* Pipeline + Results */}
      <div className="space-y-4 mt-5">
          {loading && (
            <PipelineVisualizer steps={pipelineSteps} title="Model Pipeline" />
          )}

          {!result && !loading && (
            <div className="flex flex-col items-center justify-center h-[400px] rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)]">
              <ShieldAlert className="w-12 h-12 text-[var(--color-text-muted)] opacity-30 mb-3" />
              <p className="text-base text-[var(--color-text-muted)]">Select disease, state, and run a scenario</p>
            </div>
          )}

          {result && (
            <>
              {/* Zone 1: Risk Score */}
              <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-5">
                <div className="flex items-center gap-4 mb-4">
                  <span className="text-sm font-semibold text-white">{disease.name}</span>
                  <StatusBadge status="live" />
                  <span className="text-sm text-[var(--color-text-muted)] font-mono">{result.state} · {result.projection_year}</span>
                  <span className="text-sm text-[var(--color-text-muted)] font-mono">R₀={result.outbreak_summary.avg_reproduction_rate} · CFR={result.outbreak_summary.avg_case_fatality_rate}%</span>
                </div>
                <div className="flex items-center justify-center gap-8 flex-wrap">
                  <RiskGauge score={result.tolerability.risk_score} level={result.tolerability.risk_level} verdict={result.tolerability.verdict} />
                  <div className="grid grid-cols-2 gap-x-8 gap-y-4">
                    <SatelliteMetric label="Total Cases" value={result.outbreak_summary.total_confirmed_cases} color="var(--color-accent-cyan)" />
                    <SatelliteMetric label="Deaths" value={result.outbreak_summary.total_deaths} color="var(--color-accent-rose)" />
                    <SatelliteMetric label="Bed Demand" value={result.projected_impact.projected_bed_demand} color="var(--color-accent-violet)" />
                    <SatelliteMetric label="CFR" value={`${result.outbreak_summary.avg_case_fatality_rate}%`} color="var(--color-accent-amber)" />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* Zone 2: Timeline */}
                <div className="lg:col-span-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-5">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-semibold text-white">Monthly Forecast</h3>
                    <div className="flex gap-1 p-0.5 rounded-md bg-[var(--color-surface-2)]">
                      <button onClick={() => setShowCases(true)}
                        className={`px-2.5 py-1 text-xs font-mono rounded transition-all ${showCases ? 'bg-[var(--color-accent-cyan)] text-black' : 'text-[var(--color-text-muted)]'}`}>Cases</button>
                      <button onClick={() => setShowCases(false)}
                        className={`px-2.5 py-1 text-xs font-mono rounded transition-all ${!showCases ? 'bg-[var(--color-accent-rose)] text-black' : 'text-[var(--color-text-muted)]'}`}>Deaths</button>
                    </div>
                  </div>
                  <div className="h-[260px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" vertical={false} />
                        <XAxis dataKey="month" stroke="var(--color-text-muted)" tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }} tickLine={false} axisLine={false} />
                        <YAxis stroke="var(--color-text-muted)" tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }} tickLine={false} axisLine={false} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)} />
                        <Tooltip cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                          contentStyle={{ background: 'rgba(11,17,32,0.9)', border: '1px solid var(--color-border-subtle)', borderRadius: '8px', fontSize: '11px' }} />
                        <ReferenceLine x={new Date().toLocaleString('default', { month: 'short' }).slice(0, 3)} stroke="var(--color-accent-amber)" strokeDasharray="4 4" label={{ value: 'TODAY', fill: 'var(--color-accent-amber)', fontSize: 9 }} />
                        <Bar dataKey={showCases ? 'confirmed_cases' : 'deaths'}
                          fill={showCases ? disease.color : 'var(--color-accent-rose)'}
                          radius={[3, 3, 0, 0]} maxBarSize={24}
                          animationBegin={200} animationDuration={800} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Zone 3: Intelligence Panel */}
                <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-5 space-y-4">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Info className="w-3.5 h-3.5 text-[var(--color-accent-amber)]" />
                    Intelligence Briefing
                  </h3>
                  <div className="space-y-2">
                    {result.recommendations.map((rec, i) => (
                      <div key={i} className="p-2.5 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-2)] text-xs leading-relaxed"
                        style={{
                          borderLeft: `3px solid ${i === 0 ? 'var(--color-accent-rose)' : i === 1 ? 'var(--color-accent-amber)' : 'var(--color-accent-cyan)'}`
                        }}>
                        <span className="text-[11px] font-mono text-[var(--color-text-muted)]">PRIORITY {i + 1}</span>
                        <p className="text-[var(--color-text-primary)] mt-0.5">{rec}</p>
                      </div>
                    ))}
                  </div>

                  {/* At-risk hospitals */}
                  {result.hospitals_at_risk.length > 0 && (
                    <div>
                      <p className="text-xs font-mono text-[var(--color-text-muted)] uppercase tracking-wider mb-2">At-Risk Hospitals</p>
                      <div className="space-y-1 max-h-[180px] overflow-y-auto">
                        {result.hospitals_at_risk.map((h: HospitalRiskItem, i: number) => (
                          <div key={i}>
                            <button
                              onClick={() => setExpandedHospital(expandedHospital === i ? null : i)}
                              className="w-full flex items-center justify-between p-2 rounded-lg text-sm text-left hover:bg-[var(--color-surface-2)] transition-colors"
                            >
                              <span className="text-[var(--color-text-primary)] truncate flex-1">{h.name}</span>
                              <span className="text-[var(--color-text-muted)] font-mono text-xs">{h.beds} beds</span>
                              <ChevronRight className={`w-3 h-3 text-[var(--color-text-muted)] transition-transform ${expandedHospital === i ? 'rotate-90' : ''}`} />
                            </button>
                            {expandedHospital === i && (
                              <div className="px-2 pb-2 text-xs text-[var(--color-text-muted)] font-mono space-y-0.5">
                                <p>{h.district} · {h.type}</p>
                                <p>ICU: {h.icu_beds} · Specialists: {h.specialists}</p>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
    </div>
  );
}

import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, ShieldAlert, Syringe, Plane, Users, Activity, AlertTriangle, ChevronRight, Info } from 'lucide-react';
import { getPatient, getPatientRisk } from '../api';
import { PatientDetailData, PatientRiskResponse, VaccineRecord, TravelRecord, FamilyRecord } from '../types/api';
import PipelineVisualizer from '../components/ui/PipelineVisualizer';
import StatusBadge from '../components/ui/StatusBadge';
import Button from '../components/ui/Button';

const VIRUS_NAMES = ['COVID-19', 'Ebola', 'H1N1', 'Marburg', 'Nipah', 'SARS'];
const AVATAR_COLORS = [
  'from-cyan-500 to-blue-600', 'from-violet-500 to-purple-600', 'from-emerald-500 to-teal-600',
  'from-rose-500 to-pink-600', 'from-amber-500 to-orange-600', 'from-indigo-500 to-blue-600',
];

function getInitialColor(id: number): string {
  return AVATAR_COLORS[id % AVATAR_COLORS.length];
}

function getInitials(name: string): string {
  if (!name) return '?';
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
}

const PIPELINE_STEPS = [
  { label: 'Loading patient profile...', status: 'pending' as const },
  { label: 'Running RandomForest model...', status: 'pending' as const },
  { label: 'Running GradientBoosting model...', status: 'pending' as const },
  { label: 'Running XGBoost model...', status: 'pending' as const },
  { label: 'Ensemble aggregation...', status: 'pending' as const },
  { label: 'Computing risk score...', status: 'pending' as const },
];

function RiskGauge({ score }: { score: number }) {
  const [animatedScore, setAnimatedScore] = useState(0);
  const ref = useRef<number>(0);

  useEffect(() => {
    const duration = 1200;
    const start = performance.now();
    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimatedScore(Math.round(score * eased));
      if (progress < 1) ref.current = requestAnimationFrame(animate);
    };
    ref.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(ref.current);
  }, [score]);

  const getColor = () => {
    if (score < 30) return 'var(--color-accent-emerald)';
    if (score < 55) return 'var(--color-accent-amber)';
    if (score < 80) return '#f97316';
    return 'var(--color-accent-rose)';
  };

  const color = getColor();
  const r = 60;
  const circ = Math.PI * r;
  const offset = circ - (animatedScore / 100) * circ;

  return (
    <div className="flex flex-col items-center">
      <svg width="160" height="100" viewBox="0 0 160 120">
        <path d="M 20 100 A 60 60 0 0 1 140 100" fill="none" stroke="var(--color-surface-3)" strokeWidth="12" strokeLinecap="round" />
        <path d="M 20 100 A 60 60 0 0 1 140 100" fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.3s ease' }} />
        <text x="80" y="70" textAnchor="middle" fill="white" fontSize="28" fontWeight="bold" fontFamily="var(--font-mono)">{animatedScore}</text>
        <text x="80" y="88" textAnchor="middle" fill="var(--color-text-muted)" fontSize="9">Risk Score</text>
      </svg>
    </div>
  );
}

function FeatureBar({ name, value, weight, category }: { name: string; value: number; weight: number; category: string }) {
  const pct = Math.min(value * 100, 100);
  const opacity = 0.3 + weight * 0.7;
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-[10px]">
        <span className="text-[var(--color-text-muted)] truncate">{name}</span>
        <span className="text-[var(--color-text-primary)] font-mono">{pct.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-[var(--color-surface-3)] overflow-hidden">
        <div className="h-full rounded-full bg-gradient-to-r from-[var(--color-accent-cyan)] to-[var(--color-accent-violet)]"
          style={{ width: `${pct}%`, opacity, transition: 'width 0.8s cubic-bezier(0.34, 1.56, 0.64, 1)' }} />
      </div>
    </div>
  );
}

export default function PatientDetail() {
  useEffect(() => { document.title = 'Patient Detail | HOSPi'; }, []);
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<PatientDetailData | null>(null);
  const [virus, setVirus] = useState('COVID-19');
  const [risk, setRisk] = useState<PatientRiskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [riskLoading, setRiskLoading] = useState(false);
  const [error, setError] = useState('');
  const [pipelineStep, setPipelineStep] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!id) return;
    getPatient<PatientDetailData>(id)
      .then(d => setData(d))
      .catch((e: any) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, []);

  const computeRisk = () => {
    if (!id) return;
    setRiskLoading(true);
    setRisk(null);
    setPipelineStep(0);
    const steps = ['patient', 'rf', 'gb', 'xgb', 'ensemble', 'score'];
    let i = 0;

    intervalRef.current = setInterval(() => {
      i++;
      if (i >= 5) { clearInterval(intervalRef.current!); }
      setPipelineStep(Math.min(i, 5));
    }, 350);

    getPatientRisk<PatientRiskResponse>(id, virus)
      .then(d => { setRisk(d); setPipelineStep(6); })
      .catch((e: any) => setError(e.message))
      .finally(() => { clearInterval(intervalRef.current!); setRiskLoading(false); });
  };

  if (loading) return (
    <div className="flex justify-center py-20">
      <div className="w-6 h-6 border-2 border-[var(--color-accent-cyan)] border-t-transparent rounded-full animate-spin" />
    </div>
  );
  if (!data) return (
    <div className="flex items-center justify-center py-20 text-sm text-[var(--color-text-muted)]">
      <ShieldAlert className="w-6 h-6 mr-2 opacity-50" /> Patient not found
    </div>
  );

  const patient = ('patient' in data ? (data as any).patient : data) as Record<string, any>;
  const vaccine_history: VaccineRecord[] = data.vaccine_history || ('vaccine_history' in data ? (data as any).vaccine_history || [] : []);
  const travel_history: TravelRecord[] = data.travel_history || ('travel_history' in data ? (data as any).travel_history || [] : []);
  const family_history: FamilyRecord[] = data.family_history || ('family_history' in data ? (data as any).family_history || [] : []);

  const patientId = patient.id || (data as any).id || 0;
  const patientName = patient.patient_name || (data as any).patient_name || 'Unknown';
  const age = patient.age || (data as any).age;
  const bloodGroup = patient.blood_group || (data as any).blood_group || 'N/A';
  const gender = patient.gender || (data as any).gender || 'N/A';
  const state = patient.state || (data as any).state || 'N/A';
  const district = patient.district || (data as any).district || 'N/A';
  const dob = patient.dob || (data as any).dob || 'N/A';
  const contact = patient.contact || (data as any).contact || 'N/A';
  const preExisting = patient.pre_existing_conditions || (data as any).pre_existing_conditions || '';

  const categoryOrder = ['demographic', 'medical', 'lifestyle', 'genetic'];
  const categoryLabels: Record<string, string> = { demographic: 'Demographic', medical: 'Medical History', lifestyle: 'Lifestyle', genetic: 'Genetic' };
  const groupedFeatures: Record<string, any[]> = {};

  if (risk?.features) {
    for (const f of risk.features) {
      const cat = f.category || 'other';
      if (!groupedFeatures[cat]) groupedFeatures[cat] = [];
      groupedFeatures[cat].push(f);
    }
  }

  const pipelineSteps = PIPELINE_STEPS.map((s, i) => ({
    ...s,
    status: i < pipelineStep ? 'done' as const : i === pipelineStep && pipelineStep < 6 && riskLoading ? 'running' as const : s.status,
  }));

  return (
    <div className="space-y-4">
      <Link to="/dashboard/patients"
        className="inline-flex items-center gap-1.5 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-accent-cyan)] transition-colors">
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Patients
      </Link>

      {error && (
        <div className="flex items-center gap-2 text-sm text-[var(--color-accent-rose)] bg-[var(--color-accent-rose)]/10 rounded-lg px-3 py-2">
          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" /> {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr_280px] gap-4">
        {/* Panel 1: Identity */}
        <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-5">
          <div className="flex flex-col items-center text-center">
            <div className={`w-20 h-20 rounded-full bg-gradient-to-br ${getInitialColor(patientId)} flex items-center justify-center text-2xl font-bold text-white mb-3`}>
              {getInitials(patientName)}
            </div>
            <h2 className="text-2xl font-bold text-white">{patientName}</h2>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 w-full mt-4 text-sm">
              <div><span className="text-[var(--color-text-muted)]">Age</span><p className="text-white font-mono mt-0.5">{age || 'N/A'}</p></div>
              <div><span className="text-[var(--color-text-muted)]">Gender</span><p className="text-white mt-0.5">{gender}</p></div>
              <div><span className="text-[var(--color-text-muted)]">Blood</span><p className="text-white font-mono mt-0.5">{bloodGroup}</p></div>
              <div><span className="text-[var(--color-text-muted)]">DOB</span><p className="text-white font-mono mt-0.5 text-xs">{dob}</p></div>
              <div className="col-span-2"><span className="text-[var(--color-text-muted)]">State</span><p className="text-white mt-0.5">{state}{district ? ` · ${district}` : ''}</p></div>
              <div className="col-span-2"><span className="text-[var(--color-text-muted)]">Contact</span><p className="text-white font-mono mt-0.5 text-xs break-all">{contact}</p></div>
            </div>
            {preExisting && (
              <div className="mt-3 w-full">
                <div className="flex items-start gap-1.5 text-sm p-2.5 rounded-lg bg-[var(--color-accent-amber)]/10 border border-[var(--color-accent-amber)]/20">
                  <Activity className="w-3.5 h-3.5 text-[var(--color-accent-amber)] mt-0.5 flex-shrink-0" />
                  <div><span className="text-[var(--color-text-muted)]">Pre-existing:</span><p className="text-[var(--color-accent-amber)]">{preExisting}</p></div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Panel 2: Risk Assessment */}
        <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-[var(--color-accent-rose)]" />
              Risk Assessment
            </h3>
            <StatusBadge status="ml_model" label="3-Model Ensemble" />
          </div>

          {/* Virus selector + Assess button */}
          <div className="flex items-center gap-3 mb-4">
            <div className="flex-1">
              <select value={virus} onChange={e => setVirus(e.target.value)}
                className="w-full bg-[var(--color-surface-2)] border border-[var(--color-border-subtle)] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[var(--color-accent-cyan)]">
                {VIRUS_NAMES.map(v => <option key={v} value={v} className="bg-[#0B1220] text-white">{v}</option>)}
              </select>
            </div>
            <Button variant="danger" size="sm" icon={ShieldAlert} onClick={computeRisk} isLoading={riskLoading}>
              {riskLoading ? 'Assessing...' : 'Assess Risk'}
            </Button>
          </div>

          {/* Pipeline */}
          {riskLoading && (
            <PipelineVisualizer steps={pipelineSteps} title="Model Pipeline" />
          )}

          {/* Results */}
          {risk && (
            <div className="space-y-4">
              <div className="flex items-center justify-center gap-6 flex-wrap">
                <RiskGauge score={risk.risk_score_pct !== undefined ? risk.risk_score_pct : (risk.risk_score ? risk.risk_score * 100 : 0)} />
                <div>
                  <span className="text-xs text-[var(--color-text-muted)] font-mono">Level</span>
                  <p className={`text-lg font-bold mt-0.5 ${
                    risk.risk_level === 'Low' ? 'text-emerald-400' :
                    risk.risk_level === 'Moderate' ? 'text-amber-400' :
                    risk.risk_level === 'High' ? 'text-rose-400' : 'text-[var(--color-accent-rose)]'
                  }`}>{risk.risk_level}</p>
                </div>
              </div>

              {/* Feature bars grouped by category */}
              {categoryOrder.filter(c => groupedFeatures[c]?.length).map(cat => (
                <div key={cat}>
                  <p className="text-xs font-mono text-[var(--color-text-muted)] uppercase tracking-wider mb-2">{categoryLabels[cat] || cat}</p>
                  <div className="space-y-1.5">
                    {groupedFeatures[cat].map((f, i) => (
                      <FeatureBar key={i} name={f.name} value={f.value} weight={f.weight} category={f.category} />
                    ))}
                  </div>
                </div>
              ))}

              {/* Un-categorized features */}
              {Object.entries(groupedFeatures)
                .filter(([cat]) => !categoryOrder.includes(cat))
                .map(([cat, features]) => (
                  <div key={cat}>
                    <p className="text-xs font-mono text-[var(--color-text-muted)] uppercase tracking-wider mb-2">{categoryLabels[cat] || cat}</p>
                    <div className="space-y-1.5">
                      {features.map((f, i) => (
                        <FeatureBar key={i} name={f.name} value={f.value} weight={f.weight} category={f.category} />
                      ))}
                    </div>
                  </div>
                ))}
            </div>
          )}

          {!risk && !riskLoading && (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <ShieldAlert className="w-8 h-8 text-[var(--color-text-muted)] opacity-30 mb-2" />
              <p className="text-sm text-[var(--color-text-muted)]">Select a virus and assess risk</p>
            </div>
          )}
        </div>

        {/* Panel 3: Timeline */}
        <div className="space-y-4">
          {/* Vaccine History */}
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-3">
              <Syringe className="w-3.5 h-3.5 text-emerald-400" />
              Vaccines <span className="text-[var(--color-text-muted)] font-normal">({vaccine_history.length})</span>
            </h3>
            {vaccine_history.length === 0 ? (
              <p className="text-sm text-[var(--color-text-muted)]">No vaccination records</p>
            ) : (
              <div className="space-y-2">
                {vaccine_history.map((v, i) => (
                  <div key={i} className="flex items-center gap-3 py-2 border-b border-[var(--color-border-subtle)] last:border-0">
                    <div className="w-6 h-6 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center flex-shrink-0">
                      <Syringe className="w-3 h-3 text-emerald-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white truncate">{v.vaccine_name}</p>
                      <p className="text-xs text-[var(--color-text-muted)] font-mono">{v.virus_name || 'General'} · Dose {v.dose_number}{v.vaccination_date ? ` · ${v.vaccination_date}` : ''}</p>
                    </div>
                    {v.effectiveness !== undefined && (
                      <span className="text-xs font-mono text-emerald-400">{(v.effectiveness * 100).toFixed(0)}%</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Travel History */}
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-3">
              <Plane className="w-3.5 h-3.5 text-cyan-400" />
              Travel <span className="text-[var(--color-text-muted)] font-normal">({travel_history.length})</span>
            </h3>
            {travel_history.length === 0 ? (
              <p className="text-sm text-[var(--color-text-muted)]">No travel records</p>
            ) : (
              <div className="space-y-2">
                {travel_history.map((t, i) => (
                  <div key={i} className="flex items-center gap-3 py-2 border-b border-[var(--color-border-subtle)] last:border-0">
                    <div className="w-6 h-6 rounded-full bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center flex-shrink-0">
                      <Plane className="w-3 h-3 text-cyan-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white truncate">{t.from_location} → {t.to_location}</p>
                      <p className="text-xs text-[var(--color-text-muted)] font-mono">{t.travel_date || ''}{t.return_date ? ` to ${t.return_date}` : ''}{t.purpose ? ` · ${t.purpose}` : ''}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Family History */}
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-3">
              <Users className="w-3.5 h-3.5 text-violet-400" />
              Family <span className="text-[var(--color-text-muted)] font-normal">({family_history.length})</span>
            </h3>
            {family_history.length === 0 ? (
              <p className="text-sm text-[var(--color-text-muted)]">No family history records</p>
            ) : (
              <div className="space-y-2">
                {family_history.map((f, i) => (
                  <div key={i} className="flex items-center gap-3 py-2 border-b border-[var(--color-border-subtle)] last:border-0">
                    <div className="w-6 h-6 rounded-full bg-violet-500/10 border border-violet-500/20 flex items-center justify-center flex-shrink-0">
                      <Users className="w-3 h-3 text-violet-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white truncate"><span className="text-[var(--color-text-muted)]">{f.relationship}:</span> {f.condition}</p>
                      <p className="text-xs text-[var(--color-text-muted)] font-mono">Age {f.age_at_diagnosis || '?'}{f.is_deceased ? ' · Deceased' : ''}</p>
                    </div>
                    {f.is_deceased && <AlertTriangle className="w-3.5 h-3.5 text-[var(--color-accent-rose)] flex-shrink-0" />}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

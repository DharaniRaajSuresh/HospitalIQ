import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ShieldAlert, Target, HeartPulse, Stethoscope, Search, Activity, Users, AlertTriangle } from 'lucide-react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, PieChart, Pie, Cell, Tooltip as RechartsTooltip } from 'recharts';
import GlassCard from '../components/ui/GlassCard';
import Button from '../components/ui/Button';
import { getLocationStats, getDistricts, predictMortality } from '../api';
import type { DistrictItem } from '../types/api';
import jsPDF from 'jspdf/dist/jspdf.es.js';

const COLORS = ['#f43f5e', '#f59e0b', '#3b82f6', '#10b981'];
const MOCK_CAUSES = ['Cardiac', 'Respiratory', 'Infectious', 'Cancer', 'Accident', 'Neonatal', 'Maternal'];

interface PredictMortalityResponse {
  result: {
    predicted_death_rate?: number;
    status?: string;
    [key: string]: unknown;
  };
}

export default function MortalityAnalytics() {
  const [district, setDistrict] = useState('');
  const [districts, setDistricts] = useState<DistrictItem[]>([]);

  const [ageGroup, setAgeGroup] = useState('45-64');
  const [cause, setCause] = useState('Cardiac');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [locStats, setLocStats] = useState(null);

  const [fetchError, setFetchError] = useState(null);
  const [riskScore, setRiskScore] = useState(65);
  const [riskLevel, setRiskLevel] = useState('Moderate');
  const [primaryFactor, setPrimaryFactor] = useState('Age bracket (45-64) with cardiovascular history.');

  useEffect(() => {
    getDistricts<DistrictItem[]>().then((d: DistrictItem[]) => {
      setDistricts(d);
      if (d.length && !district) setDistrict(d[0].district);
    }).catch(e => setFetchError((e as Error).message || 'Failed to load districts'));
  }, []);

  useEffect(() => {
    getLocationStats('', district).then(setLocStats).catch(e => setFetchError((e as Error).message || 'Failed to load location stats'));
  }, [district]);

  const generatePlan = () => {
    const doc = new jsPDF();
    doc.setFontSize(18);
    doc.text('Intervention Plan', 14, 22);
    doc.setFontSize(11);
    doc.text(`District: ${district}`, 14, 32);
    doc.text(`Target Cause: ${cause}`, 14, 39);
    doc.text(`Age Group: ${ageGroup}`, 14, 46);
    doc.text(`Risk Level: ${riskLevel} (Score: ${riskScore})`, 14, 53);
    doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 60);

    doc.setFontSize(14);
    doc.text('Recommended Actions', 14, 78);
    doc.setFontSize(11);
    const actions = [
      `1. Deploy mobile health units to ${district} for ${cause} screening.`,
      `2. Stock ${cause} treatment supplies at primary health centres.`,
      `3. Conduct awareness camps targeting ${ageGroup} age group.`,
      `4. Increase ICU bed capacity for ${cause} cases by 20%.`,
      `5. Schedule follow-up visits for high-risk patients in ${district}.`,
      riskLevel === 'Critical' || riskLevel === 'High' ? '6. EMERGENCY: Activate district crisis response team immediately.' : '6. Monitor mortality trends monthly and adjust resources accordingly.',
    ];
    let y = 88;
    actions.forEach(a => { doc.text(a, 14, y); y += 8; });

    if (locStats?.mortality?.common_causes) {
      doc.setFontSize(14);
      doc.text('Local Mortality Context', 14, y + 10);
      doc.setFontSize(11);
      y += 20;
      locStats.mortality.common_causes.slice(0, 5).forEach(c => {
        doc.text(`${c.cause}: ${c.deaths.toLocaleString()} deaths`, 14, y);
        y += 7;
      });
    }

    doc.save(`intervention-plan-${district.toLowerCase().replace(/\s+/g, '-')}.pdf`);
  };

  const handlePredict = async () => {
    setLoading(true);
    try {
      const data = await predictMortality({ district, age_group: ageGroup, cause, year: '2026', month: '6' }) as PredictMortalityResponse;
      const r = data.result;
      setResult(r);
      const rate = r.predicted_death_rate || 0;
      let score;
      if (rate > 150) score = 85 + Math.min(15, (rate - 150) / 3);
      else if (rate > 100) score = 65 + ((rate - 100) / 50) * 20;
      else if (rate > 60) score = 40 + ((rate - 60) / 40) * 25;
      else score = 15 + (rate / 60) * 25;
      setRiskScore(Math.min(100, Math.round(score)));
      setRiskLevel(r.risk_level || 'Moderate');
      setPrimaryFactor(`Age ${r.age_group} with ${r.cause} in ${r.district}.`);
    } catch (e) {
      setResult(null);
      setFetchError(e.message || 'Prediction failed');
    }
    setLoading(false);
  };

  const riskFactorsData = [
    { subject: 'Cardiovascular', A: Math.min(150, riskScore * 1.1 + 10), fullMark: 150 },
    { subject: 'Respiratory', A: Math.min(150, riskScore * 0.9), fullMark: 150 },
    { subject: 'Metabolic', A: Math.min(150, riskScore * 0.8 + 5), fullMark: 150 },
    { subject: 'Age Factor', A: Math.min(150, riskScore), fullMark: 150 },
    { subject: 'Comorbidities', A: Math.min(150, riskScore * 1.0 + 15), fullMark: 150 },
    { subject: 'Historical', A: Math.min(150, riskScore * 0.7), fullMark: 150 },
  ];

  const realCauses = locStats?.mortality?.common_causes || [];
  const causesData = realCauses.length > 0
    ? realCauses.slice(0, 4).map((c, i) => ({ name: c.cause, value: c.deaths, color: COLORS[i % COLORS.length] }))
    : [
        { name: 'Cardiac', value: cause === 'Cardiac' ? 400 + riskScore : 250, color: COLORS[0] },
        { name: 'Cancer', value: cause === 'Cancer' ? 400 + riskScore : 250, color: COLORS[1] },
        { name: 'Respiratory', value: cause === 'Respiratory' ? 400 + riskScore : 250, color: COLORS[2] },
        { name: 'Accident', value: 400 + riskScore, color: COLORS[3] },
      ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Mortality Risk Analytics</h1>
          <p className="text-[var(--color-text-secondary)] mt-1">Predictive risk assessment and causal analysis.</p>
        </div>
      </div>

      {fetchError && (
        <div className="flex items-center gap-2 text-sm text-red-400 bg-red-400/10 rounded-lg px-4 py-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" /> {fetchError}
        </div>
      )}
      <GlassCard className="p-4">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="text-xs text-[var(--color-text-secondary)] block mb-1">District</label>
            <select value={district} onChange={e => setDistrict(e.target.value)}
              className="bg-[var(--color-bg-primary)] border border-[var(--color-border)] text-sm rounded-lg px-3 py-2 focus:border-[var(--color-accent-rose)] outline-none text-white min-w-[140px]">
              {districts.length === 0 && <option>Loading...</option>}
              {districts.map((d, i) => <option key={i}>{d.district}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-[var(--color-text-secondary)] block mb-1">Age Group</label>
            <select value={ageGroup} onChange={e => setAgeGroup(e.target.value)}
              className="bg-[var(--color-bg-primary)] border border-[var(--color-border)] text-sm rounded-lg px-3 py-2 focus:border-[var(--color-accent-rose)] outline-none text-white min-w-[100px]">
              <option>0-14</option><option>15-44</option><option>45-64</option><option>65+</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-[var(--color-text-secondary)] block mb-1">Cause of Death</label>
            <select value={cause} onChange={e => setCause(e.target.value)}
              className="bg-[var(--color-bg-primary)] border border-[var(--color-border)] text-sm rounded-lg px-3 py-2 focus:border-[var(--color-accent-rose)] outline-none text-white min-w-[150px]">
              {MOCK_CAUSES.map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
          <Button variant="primary" icon={Search} isLoading={loading} onClick={handlePredict}
            className="w-full justify-center bg-gradient-to-r from-red-500 to-rose-500 border-none">Predict</Button>
        </div>
      </GlassCard>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <GlassCard className="lg:col-span-4 p-6 flex flex-col items-center justify-center relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-[var(--color-accent-rose)] opacity-10 blur-3xl rounded-full"></div>
          <h3 className="text-lg font-medium text-[var(--color-text-secondary)] mb-6 self-start w-full">Aggregated Risk Score</h3>

          <div className="relative w-48 h-48 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="45" fill="none" stroke="var(--color-bg-primary)" strokeWidth="8" />
              <motion.circle cx="50" cy="50" r="45" fill="none" stroke="var(--color-accent-rose)" strokeWidth="8"
                strokeDasharray="283" initial={{ strokeDashoffset: 283 }}
                animate={{ strokeDashoffset: 283 - (283 * riskScore) / 100 }}
                transition={{ duration: 1.5, ease: "easeOut" }} strokeLinecap="round" />
            </svg>
            <div className="absolute flex flex-col items-center justify-center">
              <span className="text-5xl font-bold text-white tracking-tighter">{riskScore}</span>
              <span className="text-xs font-semibold text-[var(--color-accent-rose)] tracking-wider mt-1">{riskLevel.toUpperCase()}</span>
            </div>
          </div>

          <div className="mt-8 w-full space-y-4">
            <div className="p-4 rounded-xl bg-[var(--color-bg-primary)] border border-[var(--color-border)]">
              <div className="flex items-center gap-3 mb-2">
                <Target className="w-4 h-4 text-[var(--color-accent-amber)]" />
                <span className="text-sm font-medium text-white">Primary Factor</span>
              </div>
              <p className="text-xs text-[var(--color-text-muted)]">{primaryFactor}</p>
            </div>

            {locStats && (
              <div className="p-4 rounded-xl bg-[var(--color-bg-primary)] border border-[var(--color-border)]">
                <div className="flex items-center gap-3 mb-2">
                  <Activity className="w-4 h-4 text-[var(--color-accent-cyan)]" />
                  <span className="text-sm font-medium text-white">District Stats</span>
                </div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-[var(--color-text-muted)]">Total Deaths</span>
                  <span>{locStats.mortality?.total_deaths?.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-[var(--color-text-muted)]">Death Rate</span>
                  <span>{locStats.mortality?.avg_death_rate}/100k</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-[var(--color-text-muted)]">Population</span>
                  <span>{(locStats.mortality?.total_population / 1e6).toFixed(1)}M</span>
                </div>
              </div>
            )}

            <Button variant="primary" className="w-full bg-[var(--color-accent-rose)] hover:bg-[#e11d48] border-none flex justify-center" onClick={generatePlan}>
              Generate Intervention Plan
            </Button>
          </div>
        </GlassCard>

        <div className="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-6">
          <GlassCard className="p-6">
            <h3 className="text-lg font-medium text-white mb-6 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-[var(--color-accent-cyan)]" />
              Risk Factor Analysis
            </h3>
            <div className="h-[250px] w-full">
              <ResponsiveContainer width="99%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="65%" data={riskFactorsData}>
                  <PolarGrid stroke="var(--color-border)" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--color-text-secondary)', fontSize: 10 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 150]} tick={false} axisLine={false} />
                  <Radar name="Risk Index" dataKey="A" stroke="var(--color-accent-cyan)" fill="var(--color-accent-cyan)" fillOpacity={0.3} />
                  <RechartsTooltip contentStyle={{ backgroundColor: 'var(--color-bg-card)', borderColor: 'var(--color-border)', borderRadius: '8px' }} itemStyle={{ color: '#fff' }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </GlassCard>

          <GlassCard className="p-6">
            <h3 className="text-lg font-medium text-white mb-6 flex items-center gap-2">
              <Stethoscope className="w-5 h-5 text-[var(--color-accent-amber)]" />
              Distribution of Causes
            </h3>
            <div className="h-[250px] w-full">
              <ResponsiveContainer width="99%" height="100%">
                <PieChart>
                  <Pie data={causesData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value" stroke="none">
                    {causesData.map((entry, index) => (<Cell key={`cell-${index}`} fill={entry.color || COLORS[index % COLORS.length]} />))}
                  </Pie>
                  <RechartsTooltip contentStyle={{ backgroundColor: 'var(--color-bg-card)', borderColor: 'var(--color-border)', borderRadius: '8px' }} itemStyle={{ color: '#fff' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-4">
              {causesData.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2 text-xs text-[var(--color-text-secondary)]">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color || COLORS[idx % COLORS.length] }}></div>
                  {item.name}
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}

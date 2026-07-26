import React, { useState, useEffect } from 'react';
import { BarChart3, PieChart as PieChartIcon, LineChart as LineChartIcon, Download, Star } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell } from 'recharts';
import GlassCard from '../components/ui/GlassCard';
import Button from '../components/ui/Button';
import { getStats, getHospitalDistribution, getAllDistricts, getLocationStats } from '../api';
import { downloadCsv } from '../utils/exportCsv';

import type { StatsResponse, LocationStatsResponse } from '../types/api';

const PIE_COLORS = ['#00f0ff', '#b026ff', '#ffd700', '#ff00ea'];

interface DistrictResult {
  state: string;
  district: string;
  total_beds?: number;
  hospitals?: number;
  avg_score?: number;
  success_rate?: number;
  fatality_rate?: number;
  avg_death_rate?: number;
  total_deaths?: number;
  population?: number;
}

interface DistrictRow {
  state: string;
  district: string;
  beds: number;
  hospitals: number;
  score: number;
  successRate: number;
  fatalityRate: number;
  deathRate: number;
  deaths: number;
  population: number;
}

interface StateAggEntry {
  name: string;
  beds: number;
  hospitals: number;
  deaths: number;
  districts: Set<string>;
  scores: number[];
}

interface HospitalTypeCount {
  hospital_type: string;
  count: number;
}

export default function AnalyticsDashboard() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [hospitals, setHospitals] = useState<HospitalTypeCount[]>([]);
  const [byState, setByState] = useState<DistrictRow[]>([]);
  const [allLoc, setAllLoc] = useState<LocationStatsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getStats().then(setStats).catch(e => setError(e.message));
    getLocationStats('', '').then(setAllLoc).catch(e => setError(e.message));
    
    getHospitalDistribution().then(dist => {
      const g = dist?.["Government"] || 0;
      const p = dist?.["Private"] || 0;
      const o = dist?.["Trust/Other"] || 0;
      setHospitals([{hospital_type: "Govt", count: g}, {hospital_type: "Private", count: p}, {hospital_type: "Trust", count: o}]);
    }).catch(e => setError(e.message));

    getAllDistricts<DistrictResult[]>().then((results: DistrictResult[]) => {
      const rows = results.map(d => ({
        state: d.state,
        district: d.district,
        beds: d.total_beds || 0, hospitals: d.hospitals || 0,
        score: d.avg_score || 0, successRate: d.success_rate || 0,
        fatalityRate: d.fatality_rate || 0, deathRate: d.avg_death_rate || 0,
        deaths: d.total_deaths || 0, population: d.population || 0,
      }));
      setByState(rows);
    }).catch(e => setError(e.message));
  }, []);

  const govtHospitals = hospitals.find(h => h.hospital_type === 'Govt')?.count || 0;
  const privateHospitals = hospitals.find(h => h.hospital_type === 'Private')?.count || 0;
  const otherHospitals = hospitals.find(h => h.hospital_type === 'Trust')?.count || 0;

  const totalFacilities = allLoc?.hospitals?.total || hospitals.length || 1000;
  const dataPie = [
    { name: 'Government', value: govtHospitals || Math.round(totalFacilities * 0.35) },
    { name: 'Private', value: privateHospitals || Math.round(totalFacilities * 0.45) },
    { name: 'Trust', value: otherHospitals || Math.round(totalFacilities * 0.2) },
  ];

  const stateAgg: Record<string, StateAggEntry> = {};
  for (const r of byState) {
    if (!stateAgg[r.state]) stateAgg[r.state] = { name: r.state, beds: 0, hospitals: 0, deaths: 0, districts: new Set(), scores: [] };
    stateAgg[r.state].beds += r.beds;
    stateAgg[r.state].hospitals += r.hospitals;
    stateAgg[r.state].deaths += r.deaths;
    stateAgg[r.state].districts.add(r.district);
    if (r.score > 0) stateAgg[r.state].scores.push(r.score);
  }
  const stateData = Object.values(stateAgg).map(s => ({
    name: s.name, beds: s.beds, hospitals: s.hospitals, deaths: s.deaths,
    districts: s.districts.size,
    avgScore: s.scores.length > 0 ? (s.scores.reduce((a, b) => a + b, 0) / s.scores.length).toFixed(1) : 0,
  })).sort((a, b) => b.beds - a.beds);

  const top5 = stateData.slice(0, 5);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Advanced Analytics</h1>
          <p className="text-[var(--color-text-secondary)] mt-1">{byState.length} districts across {stateData.length} states.</p>
        </div>
        <Button variant="secondary" icon={Download} onClick={() => downloadCsv(byState, 'district-comparison.csv')}>Export Dataset</Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <GlassCard className="p-3 text-center"><div className="text-xl font-bold text-white">{allLoc?.beds?.total_beds?.toLocaleString() || stats?.beds?.toLocaleString() || '—'}</div><div className="text-[10px] text-[var(--color-text-muted)]">Total Beds</div></GlassCard>
        <GlassCard className="p-3 text-center"><div className="text-xl font-bold text-[var(--color-accent-emerald)]">{allLoc?.hospitals?.avg_success_rate || '—'}%</div><div className="text-[10px] text-[var(--color-text-muted)]">Avg Success Rate</div></GlassCard>
        <GlassCard className="p-3 text-center"><div className="text-xl font-bold text-[var(--color-accent-rose)]">{allLoc?.hospitals?.fatality_rate || '—'}%</div><div className="text-[10px] text-[var(--color-text-muted)]">Fatality Rate</div></GlassCard>
        <GlassCard className="p-3 text-center"><div className="text-xl font-bold text-[var(--color-accent-amber)]">{allLoc?.beds?.avg_occupancy || '—'}%</div><div className="text-[10px] text-[var(--color-text-muted)]">Bed Occupancy</div></GlassCard>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <GlassCard className="col-span-1 md:col-span-2 p-6 min-h-[350px]">
          <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-[var(--color-accent-cyan)]" />
            Top 5 States by Bed Count
          </h3>
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={top5} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="neonCyanDash" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00f0ff" stopOpacity={1} />
                    <stop offset="100%" stopColor="#00f0ff" stopOpacity={0.2} />
                  </linearGradient>
                  <linearGradient id="neonVioletDash" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#b026ff" stopOpacity={1} />
                    <stop offset="100%" stopColor="#b026ff" stopOpacity={0.2} />
                  </linearGradient>
                  <filter id="glowDash" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="4" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} opacity={0.3} />
                <XAxis dataKey="name" stroke="var(--border)" tick={{ fill: '#cbd5e1' }} fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--border)" tick={{ fill: '#cbd5e1' }} fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip cursor={{ fill: 'rgba(0, 240, 255, 0.05)' }} contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.8)', backdropFilter: 'blur(10px)', borderColor: 'rgba(0, 240, 255, 0.2)', borderRadius: '12px', boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)' }} itemStyle={{ color: '#fff', fontWeight: 'bold' }} />
                <Bar dataKey="beds" name="Total Beds" fill="url(#neonCyanDash)" radius={[4, 4, 0, 0]} filter="url(#glowDash)" />
                <Bar dataKey="avgScore" name="Avg Score" fill="url(#neonVioletDash)" radius={[4, 4, 0, 0]} filter="url(#glowDash)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>

        <GlassCard className="col-span-1 p-6 min-h-[350px]">
          <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
            <PieChartIcon className="w-5 h-5 text-[var(--color-accent-violet)]" />
            Facility Distribution
          </h3>
          <div className="h-[250px] relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <defs>
                  <filter id="glowPie" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                </defs>
                <Pie data={dataPie} innerRadius={60} outerRadius={90} paddingAngle={5} dataKey="value" stroke="rgba(255,255,255,0.05)">
                  {dataPie.map((e, i) => (<Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} filter="url(#glowPie)" />))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.8)', backdropFilter: 'blur(10px)', borderColor: 'rgba(0, 240, 255, 0.2)', borderRadius: '12px', boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)' }} itemStyle={{ color: '#fff', fontWeight: 'bold' }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <span className="text-2xl font-[Outfit] font-bold text-white tracking-[-1px]">{totalFacilities.toLocaleString()}</span>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="col-span-1 md:col-span-3 p-6 min-h-[400px]">
          <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
            <LineChartIcon className="w-5 h-5 text-[var(--color-accent-emerald)]" />
            State-wise Comparison — All {stateData.length} States
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="text-[10px] text-[var(--color-text-muted)] uppercase border-b border-[var(--color-border)]">
                <tr><th className="py-2 pr-3 font-medium">State</th><th className="py-2 pr-3 font-medium">Districts</th><th className="py-2 pr-3 font-medium">Beds</th><th className="py-2 pr-3 font-medium">Hospitals</th><th className="py-2 pr-3 font-medium">Avg Score</th><th className="py-2 pr-3 font-medium">Deaths</th></tr>
              </thead>
              <tbody>
                {stateData.map((s, i) => (
                  <tr key={i} className="border-b border-[var(--color-border)] hover:bg-[var(--color-bg-elevated)]">
                    <td className="py-2 pr-3 text-white font-medium">{s.name}</td>
                    <td className="py-2 pr-3 text-[var(--color-text-secondary)]">{s.districts}</td>
                    <td className="py-2 pr-3 text-[var(--color-text-primary)]">{s.beds.toLocaleString()}</td>
                    <td className="py-2 pr-3 text-[var(--color-text-primary)]">{s.hospitals}</td>
                    <td className="py-2 pr-3 text-[var(--color-accent-emerald)]">{s.avgScore}</td>
                    <td className="py-2 pr-3 text-[var(--color-accent-rose)]">{s.deaths.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}

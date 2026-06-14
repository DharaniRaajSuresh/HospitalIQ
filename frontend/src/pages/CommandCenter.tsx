// @ts-nocheck
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Users, Building2, BedDouble, ActivitySquare, AlertTriangle, ArrowRight, Sparkles, TrendingUp, MapPin, Download } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { getStats, getLocationStats, getStates } from '../api';
import { downloadCsv } from '../utils/exportCsv';
import KPICard from '../components/ui/KPICard';
import GlassCard from '../components/ui/GlassCard';
import Button from '../components/ui/Button';
import LoadingSkeleton from '../components/ui/LoadingSkeleton';
import jsPDF from 'jspdf/dist/jspdf.es.js';

function generateReport(s, regionData, allLoc) {
  const doc = new jsPDF();
  doc.setFontSize(18);
  doc.text('HospitalIQ - Command Center Report', 14, 22);
  doc.setFontSize(11);
  doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 32);

  if (s) {
    doc.setFontSize(14);
    doc.text('System Overview', 14, 46);
    doc.setFontSize(11);
    doc.text(`States: ${s.states}`, 14, 56);
    doc.text(`Districts: ${s.districts}`, 14, 63);
    doc.text(`Hospitals: ${s.hospitals}`, 14, 70);
    doc.text(`Bed Records: ${s.beds}`, 14, 77);
    doc.text(`Mortality Records: ${s.mortality_records}`, 14, 84);
    doc.text(`Total Patients: ${s.patients}`, 14, 91);
  }

  if (allLoc) {
    doc.setFontSize(14);
    doc.text('National Averages', 14, 104);
    doc.setFontSize(11);
    doc.text(`Avg Success Rate: ${allLoc.hospitals?.avg_success_rate || 'N/A'}%`, 14, 114);
    doc.text(`Avg Death Rate: ${allLoc.mortality?.avg_death_rate || 'N/A'}`, 14, 121);
    doc.text(`Bed Occupancy: ${allLoc.beds?.avg_occupancy || 'N/A'}%`, 14, 128);
    doc.text(`Best Hospital: ${allLoc.hospitals?.best_hospital?.name || 'N/A'}`, 14, 135);
  }

  if (regionData.length > 0) {
    doc.setFontSize(14);
    doc.text('State-wise Beds', 14, 149);
    doc.setFontSize(10);
    let y = 159;
    regionData.slice(0, 20).forEach(r => {
      doc.text(`${r.name}: ${r.beds} beds`, 14, y);
      y += 7;
    });
  }

  doc.save('hospitaliq-report.pdf');
}

export default function CommandCenter() {
  const [stats, setStats] = useState(null);
  const [allLoc, setAllLoc] = useState(null);
  const [regionData, setRegionData] = useState([]);
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [s, allLoc] = await Promise.all([
          getStats(),
          getLocationStats('', '').catch(() => null),
        ]);
        setStats(s);
        setAllLoc(allLoc);

        if (s) {
          setInsights([
            { id: 1, type: 'info', message: `${s.districts} districts across ${s.states} states tracked in the system.`, time: 'Live' },
            { id: 2, type: 'success', message: `${s.beds.toLocaleString()} bed records processed. Resource planning available.`, time: 'Live' },
            { id: 3, type: 'info', message: `${s.mortality_records.toLocaleString()} mortality records analyzed for risk assessment.`, time: 'Live' },
          ]);
        }

        if (allLoc) {
          setInsights(prev => [
            ...prev,
            { id: 4, type: 'warning', message: `Best hospital: ${allLoc.hospitals.best_hospital?.name || 'N/A'} (score: ${allLoc.hospitals.best_hospital?.score || 'N/A'})`, time: 'Live' },
            { id: 5, type: 'success', message: `National avg success rate: ${allLoc.hospitals.avg_success_rate}% | Fatality rate: ${allLoc.hospitals.fatality_rate}%`, time: 'Live' },
            { id: 6, type: 'info', message: `Avg bed occupancy: ${allLoc.beds.avg_occupancy}% across ${allLoc.hospitals.total} hospitals.`, time: 'Live' },
          ]);
        }

        const stateNames = await getStates().catch(() => ['Maharashtra','Delhi','Karnataka','Tamil Nadu','Uttar Pradesh','West Bengal','Gujarat']);
        const regions = await Promise.allSettled(
          stateNames.map(s => getLocationStats(s, '').catch(() => null))
        );
        const chartData = regions
          .filter(r => r.status === 'fulfilled' && r.value)
          .map(r => r.value)
          .filter(Boolean)
          .map(d => ({
            name: d.state || 'Unknown',
            patients: d.mortality?.total_deaths || 0,
            beds: d.beds?.total_beds || 0,
            hospitals: d.hospitals?.total || 0,
            successRate: d.hospitals?.avg_success_rate || 0,
            occupancy: d.beds?.avg_occupancy || 0,
          }));
        if (chartData.length > 0) setRegionData(chartData);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <LoadingSkeleton type="dashboard" />;

  const mortalityRate = allLoc?.mortality?.avg_death_rate
    ? allLoc.mortality.avg_death_rate.toFixed(1) + '%'
    : '—';

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Command Center</h1>
          <p className="text-[var(--color-text-secondary)] mt-1">Real-time overview of healthcare intelligence.</p>
        </div>
        <div className="flex space-x-2">
          <Button variant="secondary" icon={AlertTriangle}>Critical Alerts</Button>
          <Button variant="ghost" icon={Download} onClick={() => downloadCsv(regionData, 'state-beds.csv')}>Export CSV</Button>
          <Button variant="primary" icon={ArrowRight} onClick={() => generateReport(stats, regionData, allLoc)}>Generate Report</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard label="Total Hospitals" value={allLoc?.hospitals?.total ?? stats?.hospitals ?? '—'} icon={Building2} color="violet" trend="Distinct facilities" />
        <KPICard label="Bed Records" value={stats?.beds ?? '—'} icon={BedDouble} color="emerald" trend="All India" />
        <KPICard label="Patient Admissions" value={stats?.patients ?? '—'} icon={Users} color="blue" trend="System-wide" />
        <KPICard label="Avg Death Rate" value={mortalityRate} icon={ActivitySquare} color="rose" trend={`${stats?.districts || 0} districts, ${stats?.states || 0} states`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <GlassCard className="lg:col-span-2 p-6 flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-[var(--color-accent-cyan)]" />
              State-wise Bed Distribution
            </h2>
          </div>
          <div className="flex-1" style={{ minHeight: 300 }}>
            {regionData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={regionData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="neonCyan" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#00f0ff" stopOpacity={1} />
                      <stop offset="100%" stopColor="#00f0ff" stopOpacity={0.2} />
                    </linearGradient>
                    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                      <feGaussianBlur stdDeviation="4" result="blur" />
                      <feComposite in="SourceGraphic" in2="blur" operator="over" />
                    </filter>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} opacity={0.3} />
                  <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
                  <Tooltip cursor={{ fill: 'rgba(0, 240, 255, 0.05)' }} contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.8)', backdropFilter: 'blur(10px)', borderColor: 'rgba(0, 240, 255, 0.2)', borderRadius: '12px', boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)' }} itemStyle={{ color: '#00f0ff', fontWeight: 'bold' }} />
                  <Bar dataKey="beds" name="Total Beds" fill="url(#neonCyan)" radius={[6, 6, 0, 0]} filter="url(#glow)" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-[var(--color-text-muted)]">Loading state data...</div>
            )}
          </div>
        </GlassCard>

        <GlassCard className="p-6 flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-[var(--color-accent-cyan)]" />
              Intelligence Feed
            </h2>
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--color-accent-cyan)] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[var(--color-accent-cyan)]"></span>
            </span>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto pr-2">
            {insights.map((insight, idx) => (
              <motion.div key={insight.id} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: idx * 0.05 }}
                className="p-4 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)] flex flex-col">
                <div className="flex items-start gap-3">
                  {insight.type === 'warning' && <AlertTriangle className="w-5 h-5 text-[var(--color-accent-amber)] flex-shrink-0 mt-0.5" />}
                  {insight.type === 'info' && <MapPin className="w-5 h-5 text-[var(--color-accent-blue)] flex-shrink-0 mt-0.5" />}
                  {insight.type === 'success' && <Sparkles className="w-5 h-5 text-[var(--color-accent-emerald)] flex-shrink-0 mt-0.5" />}
                  <div>
                    <p className="text-sm text-[var(--color-text-primary)] font-medium leading-snug">{insight.message}</p>
                    <p className="text-xs text-[var(--color-text-muted)] mt-1.5">{insight.time}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
          <Button variant="ghost" className="w-full mt-4 text-sm">View All Logs</Button>
        </GlassCard>
      </div>
    </div>
  );
}

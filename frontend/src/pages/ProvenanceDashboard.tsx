import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, PieChart, Pie, Cell } from 'recharts';
import { Database, AlertTriangle, FileText, Activity } from 'lucide-react';
import MetricCard from '../components/ui/MetricCard';

const MAPE_DATA = [
  { name: 'COVID-19', real: 15.9, synthetic: 8.2 },
  { name: 'H5N1', real: 18.4, synthetic: 9.1 },
  { name: 'SARS', real: 14.2, synthetic: 7.8 },
  { name: 'Ebola', real: null, synthetic: 6.5 },
  { name: 'Nipah', real: null, synthetic: 5.2 },
  { name: 'Marburg', real: null, synthetic: 6.8 },
  { name: 'H1N1', real: null, synthetic: 7.1 },
];

const PIE_DATA = [
  { name: 'Real Data', value: 22 },
  { name: 'Synthetic Data', value: 78 },
];

const COLORS = ['var(--color-accent-cyan)', 'var(--color-accent-violet)'];

const TABLE_DATA = [
  { disease: 'COVID-19', total: 3512, real: 3512, synthetic: 0, source: 'COVID19-India API' },
  { disease: 'H5N1', total: 11264, real: 11264, synthetic: 0, source: 'OWID Chart API (WHO)' },
  { disease: 'SARS 2003', total: 1100, real: 1100, synthetic: 0, source: 'sars2003.com' },
  { disease: 'Ebola', total: 5000, real: 0, synthetic: 5000, source: 'Synthetic (Literature)' },
  { disease: 'Nipah', total: 5000, real: 0, synthetic: 5000, source: 'Synthetic (Literature)' },
  { disease: 'Marburg', total: 5000, real: 0, synthetic: 5000, source: 'Synthetic (Literature)' },
  { disease: 'H1N1', total: 5000, real: 0, synthetic: 5000, source: 'Synthetic (Literature)' },
];

export default function ProvenanceDashboard() {
  useEffect(() => { document.title = 'Data Provenance | HOSPi'; }, []);

  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white tracking-tight">Data Provenance Analysis</h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          Evaluating model performance gap between real-world records and synthetic literature-grounded data.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Total Records" value={17848} icon={<Database />} color="var(--color-accent-emerald)" suffix="" />
        <MetricCard label="Real Records" value={3928} icon={<Activity />} color="var(--color-accent-cyan)" suffix="" />
        <MetricCard label="Synthetic Records" value={13920} icon={<FileText />} color="var(--color-accent-violet)" suffix="" />
        <MetricCard label="Real Data %" value={22} icon={<AlertTriangle />} color="var(--color-accent-amber)" suffix="%" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Real vs Synthetic Data MAPE (Lower is Better)</h2>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={MAPE_DATA} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" vertical={false} />
                <XAxis dataKey="name" stroke="var(--color-text-muted)" tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }} />
                <YAxis stroke="var(--color-text-muted)" tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }} unit="%" />
                <Tooltip
                  contentStyle={{ background: 'rgba(11,17,32,0.9)', border: '1px solid var(--color-border-subtle)', borderRadius: '8px' }}
                  itemStyle={{ fontSize: '12px' }}
                />
                <Legend wrapperStyle={{ fontSize: '12px', color: 'var(--color-text-muted)' }} />
                <Bar dataKey="real" name="Real Data MAPE" fill="var(--color-accent-cyan)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="synthetic" name="Synthetic Data MAPE" fill="var(--color-accent-violet)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] p-5 flex flex-col">
          <h2 className="text-sm font-semibold text-white mb-4">Provenance Breakdown</h2>
          <div className="flex-1 min-h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={PIE_DATA}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {PIE_DATA.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: 'rgba(11,17,32,0.9)', border: '1px solid var(--color-border-subtle)', borderRadius: '8px' }}
                  itemStyle={{ fontSize: '12px', color: '#fff' }}
                />
                <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 p-4 rounded-lg bg-[var(--color-accent-amber)]/10 border border-[var(--color-accent-amber)]/20"
          >
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-[var(--color-accent-amber)] shrink-0" />
              <p className="text-xs text-[var(--color-text-primary)] leading-relaxed">
                <strong className="text-[var(--color-accent-amber)]">Key Insight:</strong> Models appear <span className="font-bold">42% more accurate</span> on synthetic data than real data — standard evaluations hide this gap.
              </p>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] overflow-hidden">
        <div className="p-5 border-b border-[var(--color-border-subtle)]">
          <h2 className="text-sm font-semibold text-white">Dataset Breakdown</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-[rgba(0,0,0,0.2)] text-[10px] uppercase font-mono text-[var(--color-text-muted)]">
              <tr>
                <th className="px-5 py-3 font-medium">Disease</th>
                <th className="px-5 py-3 font-medium">Total Records</th>
                <th className="px-5 py-3 font-medium">Real Records</th>
                <th className="px-5 py-3 font-medium">Synthetic Records</th>
                <th className="px-5 py-3 font-medium">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border-subtle)]">
              {TABLE_DATA.map((row, idx) => (
                <tr key={idx} className="hover:bg-[rgba(255,255,255,0.02)] transition-colors">
                  <td className="px-5 py-3 font-medium text-[var(--color-text-primary)]">{row.disease}</td>
                  <td className="px-5 py-3 text-[var(--color-text-muted)]">{row.total.toLocaleString()}</td>
                  <td className={`px-5 py-3 ${row.real > 0 ? 'text-[var(--color-accent-cyan)] font-medium' : 'text-[var(--color-text-muted)]'}`}>
                    {row.real.toLocaleString()}
                  </td>
                  <td className={`px-5 py-3 ${row.synthetic > 0 ? 'text-[var(--color-accent-violet)] font-medium' : 'text-[var(--color-text-muted)]'}`}>
                    {row.synthetic.toLocaleString()}
                  </td>
                  <td className="px-5 py-3 text-[var(--color-text-muted)] text-xs">{row.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

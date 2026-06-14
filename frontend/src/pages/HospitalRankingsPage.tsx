// @ts-nocheck
import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Trophy, Star, Filter, ArrowUpDown, Building, MapPin, ChevronLeft, ChevronRight, Activity, BedDouble, Clock, Award, Download } from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import LoadingSkeleton from '../components/ui/LoadingSkeleton';
import { getHospitalRankings } from '../api';
import { downloadCsv } from '../utils/exportCsv';

const PAGE_SIZE = 50;
const DISEASES = ['', 'Cancer', 'Cardiac', 'Dengue', 'Diabetes', 'Hepatitis', 'Malaria', 'Orthopedic', 'Pneumonia', 'Renal', 'Stroke', 'Tuberculosis', 'Typhoid'];
const TYPES = ['', 'Government', 'Private', 'Trust'];

export default function HospitalRankingsPage() {
  const [rankings, setRankings] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [filterDisease, setFilterDisease] = useState('');
  const [filterType, setFilterType] = useState('');

  // Reset page when filters change
  useEffect(() => {
    setPage(0);
  }, [filterDisease, filterType]);

  useEffect(() => {
    setLoading(true);
    getHospitalRankings({ 
      limit: PAGE_SIZE, 
      offset: page * PAGE_SIZE, 
      disease: filterDisease, 
      hospital_type: filterType 
    }).then(data => {
      setRankings(data || []);
      setTotalCount(data._total || 0);
      setLoading(false);
    }).catch(() => {
      setRankings([]);
      setTotalCount(0);
      setLoading(false);
    });
  }, [page, filterDisease, filterType]);

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  return (
    <div className="space-y-6 flex flex-col h-full min-h-[calc(100vh-8rem)]">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Facility Leaderboard</h1>
          <p className="text-[var(--color-text-secondary)] mt-1">All {totalCount.toLocaleString()} hospitals across India.</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button variant="secondary" size="sm" icon={Download}
            onClick={async () => {
              const data = await getHospitalRankings({ limit: 1000, disease: filterDisease, hospital_type: filterType });
              downloadCsv(data.map(h => ({ 'Hospital': h.hospital_name, 'State': h.state, 'District': h.district, 'Type': h.hospital_type, 'Disease': h.disease, 'Success Rate': h.success_rate, 'Beds': h.total_beds, 'Rating': (h.rating * 5).toFixed(1) })), 'top-1000-hospitals.csv');
            }}>Export Top 1000</Button>
          <select value={filterDisease} onChange={e => setFilterDisease(e.target.value)}
            className="bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-sm text-white rounded-lg px-3 py-2 focus:outline-none focus:border-[var(--color-accent-amber)]">
            <option value="">All Diseases</option>
            {DISEASES.filter(Boolean).map(d => <option key={d}>{d}</option>)}
          </select>
          <select value={filterType} onChange={e => setFilterType(e.target.value)}
            className="bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-sm text-white rounded-lg px-3 py-2 focus:outline-none focus:border-[var(--color-accent-amber)]">
            <option value="">All Types</option>
            {TYPES.filter(Boolean).map(t => <option key={t}>{t}</option>)}
          </select>
        </div>
      </div>

      <GlassCard className="flex-1 overflow-hidden flex flex-col shadow-lg border border-[var(--color-border)]">
        <div className="overflow-x-auto flex-1">
          {loading ? (
            <div className="p-6"><LoadingSkeleton type="table" /></div>
          ) : rankings.length === 0 ? (
            <div className="p-12 text-center text-[var(--color-text-muted)]">No hospitals match the selected filters.</div>
          ) : (
            <table className="w-full text-sm text-left whitespace-nowrap">
              <thead className="text-xs text-[var(--color-text-muted)] uppercase bg-[var(--color-bg-primary)] sticky top-0 z-10 border-b border-[var(--color-border)]">
                <tr>
                  <th className="px-4 py-4 font-medium">#</th>
                  <th className="px-4 py-4 font-medium">Hospital</th>
                  <th className="px-4 py-4 font-medium">Location</th>
                  <th className="px-4 py-4 font-medium">Type</th>
                  <th className="px-4 py-4 font-medium">Disease</th>
                  <th className="px-4 py-4 font-medium">Success Rate</th>
                  <th className="px-4 py-4 font-medium">Beds</th>
                  <th className="px-4 py-4 font-medium">Avg Stay</th>
                  <th className="px-4 py-4 font-medium text-right">Rating</th>
                </tr>
              </thead>
              <tbody>
                {rankings.map((h, index) => (
                  <motion.tr key={`${h.hospital_id}-${h.disease}-${index}`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: (index % PAGE_SIZE) * 0.02 }}
                    className="border-b border-[var(--color-border)] hover:bg-[var(--color-bg-elevated)] transition-colors group cursor-pointer">
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-[var(--color-bg-primary)] border border-[var(--color-border)] text-white font-bold group-hover:border-[var(--color-accent-amber)] text-xs">
                        {page * PAGE_SIZE + index + 1}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-semibold text-white text-sm">{h.hospital_name}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col">
                        <span className="text-[var(--color-text-primary)] text-xs">{h.district}</span>
                        <span className="text-[10px] text-[var(--color-text-muted)] flex items-center gap-1">
                          <MapPin className="w-2.5 h-2.5" /> {h.state}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={h.hospital_type === 'Govt' || h.hospital_type === 'Government' ? 'info' : 'secondary'} className="text-[10px]">
                        {h.hospital_type === 'Govt' ? 'Government' : h.hospital_type}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-xs text-[var(--color-text-secondary)]">{h.disease}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-[var(--color-accent-emerald)] text-sm">{h.success_rate}%</span>
                        <div className="w-12 h-1.5 bg-[var(--color-bg-primary)] rounded-full overflow-hidden">
                          <div className="h-full bg-[var(--color-accent-emerald)]" style={{ width: `${h.success_rate}%` }}></div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-[var(--color-text-primary)]">{h.total_beds}</td>
                    <td className="px-4 py-3 text-xs text-[var(--color-text-primary)]">{h.avg_stay_days}d</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1 font-bold text-white text-sm">
                        {(h.rating * 5).toFixed(1)} <Star className="w-3.5 h-3.5 text-[var(--color-accent-amber)] fill-[var(--color-accent-amber)]" />
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-3 border-t border-[var(--color-border)] bg-[var(--color-bg-primary)]">
            <span className="text-xs text-[var(--color-text-muted)]">
              Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, totalCount)} of {totalCount.toLocaleString()}
            </span>
            <div className="flex gap-1">
              <button disabled={page === 0} onClick={() => setPage(p => p - 1)}
                className="p-1.5 rounded-md bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-[var(--color-text-secondary)] disabled:opacity-30 hover:text-white">
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}
                className="p-1.5 rounded-md bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-[var(--color-text-secondary)] disabled:opacity-30 hover:text-white">
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </GlassCard>
    </div>
  );
}

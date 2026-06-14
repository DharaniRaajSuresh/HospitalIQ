// @ts-nocheck
import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Download, Shield, ArrowUpDown, Filter, MapPin } from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';
import Badge from '../components/ui/Badge';
import { getAllDistricts } from '../api';
import { downloadCsv } from '../utils/exportCsv';

export default function IntelligenceMap() {
  const [districts, setDistricts] = useState([]);
  const [search, setSearch] = useState('');
  const [sortField, setSortField] = useState('deathRate');
  const [sortDir, setSortDir] = useState('desc');
  const [filterRisk, setFilterRisk] = useState('all');
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const allDistricts = await getAllDistricts();
        const loaded = allDistricts.map(d => {
          const deathRate = d.avg_death_rate || 0;
          return {
            name: d.district, state: d.state,
            risk: deathRate > 100 ? 'high' : deathRate > 60 ? 'medium' : 'low',
            beds: d.total_beds || 0, deathRate,
            hospitals: d.hospitals || 0, avgScore: d.avg_score || 0,
            successRate: d.success_rate || 0, fatalityRate: d.fatality_rate || 0,
            totalDeaths: d.total_deaths || 0, population: d.population || 0,
            bedOccupancy: d.bed_occupancy || 0,
          };
        });
        setDistricts(loaded.sort((a, b) => b.deathRate - a.deathRate));
      } catch { /* ignore */ }
      setLoading(false);
    })();
  }, []);

  const handleSort = (field) => {
    setSortDir(prev => sortField === field ? (prev === 'asc' ? 'desc' : 'asc') : 'desc');
    setSortField(field);
  };

  const filtered = useMemo(() => {
    let data = [...districts];
    const q = search.toLowerCase();
    if (q) data = data.filter(d => d.name.toLowerCase().includes(q) || d.state.toLowerCase().includes(q));
    if (filterRisk !== 'all') data = data.filter(d => d.risk === filterRisk);
    data.sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1;
      return a[sortField] > b[sortField] ? dir : a[sortField] < b[sortField] ? -dir : 0;
    });
    return data;
  }, [districts, search, sortField, sortDir, filterRisk]);

  const stats = useMemo(() => {
    if (!districts.length) return { total: 0, high: 0, medium: 0, low: 0, totalBeds: 0, totalHospitals: 0 };
    return {
      total: districts.length,
      high: districts.filter(d => d.risk === 'high').length,
      medium: districts.filter(d => d.risk === 'medium').length,
      low: districts.filter(d => d.risk === 'low').length,
      totalBeds: districts.reduce((s, d) => s + d.beds, 0),
      totalHospitals: districts.reduce((s, d) => s + d.hospitals, 0),
    };
  }, [districts]);

  const SortHeader = ({ field, children }) => (
    <button onClick={() => handleSort(field)}
      className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-gray-400 hover:text-gray-600 font-semibold transition-colors whitespace-nowrap">
      {children}
      <ArrowUpDown className={`w-3 h-3 ${sortField === field ? 'text-blue-500' : ''}`} />
    </button>
  );

  return (
    <div className="space-y-6">
      <GlassCard className="p-5">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-lg font-bold text-white">District Intelligence</h1>
          <button onClick={() => downloadCsv(filtered.map(d => ({
            'District': d.name, 'State': d.state, 'Risk': d.risk,
            'Beds': d.beds, 'Death Rate/100k': d.deathRate?.toFixed(1),
            'Hospitals': d.hospitals, 'Success Rate': d.successRate.toFixed(1) + '%',
            'Fatality Rate': d.fatalityRate.toFixed(1) + '%', 'Avg Score': d.avgScore.toFixed(1),
            'Deaths': d.totalDeaths, 'Population': d.population,
          })), 'districts.csv')}
            className="flex items-center gap-1.5 text-xs bg-blue-900/50 text-blue-400 px-3 py-1.5 rounded-lg hover:bg-blue-900 transition-colors">
            <Download className="w-3.5 h-3.5" /> CSV
          </button>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-4">
          <div className="bg-[#1e293b] rounded-xl p-3 border border-gray-700">
            <div className="text-2xl font-bold text-white">{stats.total}</div>
            <div className="text-[10px] text-gray-400">Districts</div>
          </div>
          <div className="bg-red-900/20 rounded-xl p-3 border border-red-900/50">
            <div className="text-2xl font-bold text-red-400">{stats.high}</div>
            <div className="text-[10px] text-red-500">High Risk</div>
          </div>
          <div className="bg-orange-900/20 rounded-xl p-3 border border-orange-900/50">
            <div className="text-2xl font-bold text-orange-400">{stats.medium}</div>
            <div className="text-[10px] text-orange-500">Medium Risk</div>
          </div>
          <div className="bg-blue-900/20 rounded-xl p-3 border border-blue-900/50">
            <div className="text-2xl font-bold text-blue-400">{stats.low}</div>
            <div className="text-[10px] text-blue-500">Low Risk</div>
          </div>
          <div className="bg-[#1e293b] rounded-xl p-3 border border-gray-700">
            <div className="text-2xl font-bold text-white">{(stats.totalBeds / 1000).toFixed(0)}k</div>
            <div className="text-[10px] text-gray-400">Total Beds</div>
          </div>
          <div className="bg-[#1e293b] rounded-xl p-3 border border-gray-700">
            <div className="text-2xl font-bold text-white">{stats.totalHospitals.toLocaleString()}</div>
            <div className="text-[10px] text-gray-400">Hospitals</div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input type="text" value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search district or state..."
              className="w-full bg-[#1e293b] border border-gray-700 text-white text-sm rounded-lg pl-9 pr-3 py-2 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 placeholder:text-gray-500" />
          </div>
          <div className="flex gap-1.5">
            {['all', 'high', 'medium', 'low'].map(r => (
              <button key={r} onClick={() => setFilterRisk(r)}
                className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                  filterRisk === r
                    ? 'bg-[#00f0ff]/20 text-[#00f0ff] border-[#00f0ff]/50'
                    : 'bg-[#1e293b] text-gray-400 border-gray-700 hover:border-gray-500'
                }`}>
                {r === 'all' ? 'All' : r.charAt(0).toUpperCase() + r.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </GlassCard>

      <GlassCard className="p-0 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
            <div className="text-sm text-gray-400">Loading districts...</div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-gray-700 bg-[#1e293b]">
                  <th className="px-4 py-3"><SortHeader field="name">District</SortHeader></th>
                  <th className="px-4 py-3"><SortHeader field="state">State</SortHeader></th>
                  <th className="px-4 py-3"><SortHeader field="risk">Risk</SortHeader></th>
                  <th className="px-4 py-3 text-right"><SortHeader field="deathRate">Death Rate</SortHeader></th>
                  <th className="px-4 py-3 text-right"><SortHeader field="beds">Beds</SortHeader></th>
                  <th className="px-4 py-3 text-right"><SortHeader field="hospitals">Hospitals</SortHeader></th>
                  <th className="px-4 py-3 text-right"><SortHeader field="successRate">Success %</SortHeader></th>
                  <th className="px-4 py-3 text-right"><SortHeader field="avgScore">Score</SortHeader></th>
                  <th className="px-4 py-3 text-right"><SortHeader field="population">Population</SortHeader></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((d, i) => (
                  <React.Fragment key={`${d.state}-${d.name}`}>
                    <tr onClick={() => setExpanded(expanded === `${d.state}-${d.name}` ? null : `${d.state}-${d.name}`)}
                      className={`border-b border-gray-800 text-xs cursor-pointer transition-colors ${
                        expanded === `${d.state}-${d.name}` ? 'bg-[#1e293b]/50' : 'hover:bg-[#1e293b]'
                      }`}>
                      <td className="px-4 py-3 font-medium text-gray-200">
                        <div className="flex items-center gap-2">
                          <MapPin className="w-3 h-3 text-blue-400 flex-shrink-0" />
                          {d.name}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-400">{d.state}</td>
                      <td className="px-4 py-3">
                        <Badge variant={d.risk === 'high' ? 'danger' : d.risk === 'medium' ? 'warning' : 'success'}
                          className="text-[10px]">{d.risk.toUpperCase()}</Badge>
                      </td>
                      <td className={`px-4 py-3 text-right font-semibold ${
                        d.deathRate > 100 ? 'text-red-400' : d.deathRate > 60 ? 'text-orange-400' : 'text-blue-400'
                      }`}>{d.deathRate.toFixed(1)}</td>
                      <td className="px-4 py-3 text-right text-gray-300">{d.beds.toLocaleString()}</td>
                      <td className="px-4 py-3 text-right text-gray-300">{d.hospitals}</td>
                      <td className="px-4 py-3 text-right text-emerald-400 font-medium">{d.successRate.toFixed(1)}%</td>
                      <td className="px-4 py-3 text-right text-gray-300">{d.avgScore.toFixed(1)}</td>
                      <td className="px-4 py-3 text-right text-gray-500">{(d.population / 1e6).toFixed(1)}M</td>
                    </tr>
                    {expanded === `${d.state}-${d.name}` && (
                      <tr className="bg-[#0f172a] border-b border-gray-800">
                        <td colSpan={9} className="px-8 py-4">
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                            <div>
                              <div className="text-[10px] text-gray-500 uppercase tracking-wider">Total Deaths</div>
                              <div className="text-sm font-semibold text-gray-200">{d.totalDeaths.toLocaleString()}</div>
                            </div>
                            <div>
                              <div className="text-[10px] text-gray-500 uppercase tracking-wider">Fatality Rate</div>
                              <div className="text-sm font-semibold text-red-400">{d.fatalityRate.toFixed(1)}%</div>
                            </div>
                            <div>
                              <div className="text-[10px] text-gray-500 uppercase tracking-wider">Bed Occupancy</div>
                              <div className="text-sm font-semibold text-gray-200">{d.bedOccupancy.toFixed(1)}%</div>
                            </div>
                            <div>
                              <div className="text-[10px] text-gray-500 uppercase tracking-wider">District Size</div>
                              <div className="text-sm font-semibold text-gray-200">{(d.population / 1e6).toFixed(1)}M</div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && (
              <div className="p-8 text-center text-sm text-gray-400">No districts match your search.</div>
            )}
          </div>
        )}
      </GlassCard>
    </div>
  );
}


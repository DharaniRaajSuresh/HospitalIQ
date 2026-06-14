// @ts-nocheck
import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Search, Activity, Filter, User, ChevronRight, ShieldAlert } from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';
import { getPatients } from '../api';

export default function PatientRecords() {
  const [patients, setPatients] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [stateFilter, setStateFilter] = useState('');
  const [states, setStates] = useState([]);
  const [apiError, setApiError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    const timerId = setTimeout(() => { 
      if (!cancelled) { controller.abort(); setApiError('TIMEOUT'); setLoading(false); }
    }, 10000);
    
    getPatients({ limit: '100' }).then(d => {
      if (cancelled) return;
      setPatients(d.patients || []);
      setTotal(d.total || 0);
      const ss = [...new Set((d.patients || []).map(p => p.state).filter(Boolean))].sort();
      setStates(ss);
    }).catch(e => {
      if (cancelled) return;
      setApiError(String(e?.status || e?.message || e));
    }).finally(() => { 
      if (!cancelled) { setLoading(false); } 
      clearTimeout(timerId); 
    });
    
    return () => { cancelled = true; controller.abort(); clearTimeout(timerId); };
  }, []);

  const handleSearch = () => {
    setLoading(true);
    getPatients({ limit: '100', ...(search && { search }), ...(stateFilter && { state: stateFilter }) })
      .then(d => { setPatients(d.patients || []); })
      .catch(e => setApiError(e.message)).finally(() => setLoading(false));
  };

  useEffect(() => { handleSearch(); }, [stateFilter]);

  const riskColor = (age) => {
    if (!age) return 'text-gray-400';
    if (age > 65) return 'text-rose-400';
    if (age > 45) return 'text-amber-400';
    return 'text-emerald-400';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Patient Records</h1>
          <p className="text-sm text-gray-400 mt-1">{total.toLocaleString()} registered patients</p>
        </div>
      </div>

      <GlassCard>
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input type="text" value={search} onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              placeholder="Search by patient name..." className="w-full bg-gray-800/50 border border-gray-700 rounded-lg py-2.5 pl-10 pr-4 text-sm text-white focus:outline-none focus:border-cyan-500" />
          </div>
          <select value={stateFilter} onChange={e => setStateFilter(e.target.value)}
            className="bg-gray-800/50 border border-gray-700 rounded-lg py-2.5 px-4 text-sm text-white focus:outline-none focus:border-cyan-500">
            <option value="">All States</option>
            {states.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <button onClick={handleSearch} className="px-4 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm transition-colors flex items-center gap-2">
            <Filter className="w-4 h-4" /> Filter
          </button>
        </div>
      </GlassCard>

      {apiError && (
        <div className="p-4 bg-red-900/30 border border-red-500/50 rounded-lg text-red-300 text-sm">
          API Error: {apiError}
          <br />Token: {window.__auth_token ? (window.__auth_token.substring(0, 20) + '...') : 'NONE'}
        </div>
      )}
      {loading ? (
        <div className="flex justify-center py-12"><div className="w-8 h-8 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin"></div></div>
      ) : (
        <div className="grid gap-3">
          {patients.map((p, i) => (
            <motion.div key={p.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.02 }}>
              <Link to={`/dashboard/patients/${p.id}`} className="block">
                <GlassCard className="hover:bg-gray-800/40 transition-all cursor-pointer group">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-violet-600 flex items-center justify-center">
                        <User className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <p className="text-white font-medium group-hover:text-cyan-300 transition-colors">{p.patient_name}</p>
                        <div className="flex items-center gap-3 text-xs text-gray-400 mt-1">
                          <span className={riskColor(p.age)}>{p.age || '?'} yrs</span>
                          <span>{p.blood_group || 'N/A'}</span>
                          <span>{p.gender || 'N/A'}</span>
                          <span>{p.state || 'N/A'}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {p.pre_existing_conditions && (
                        <span className="text-xs px-2 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          {p.pre_existing_conditions.split(',').length} condition{p.pre_existing_conditions.split(',').length > 1 ? 's' : ''}
                        </span>
                      )}
                      <ChevronRight className="w-4 h-4 text-gray-500 group-hover:text-cyan-400 transition-colors" />
                    </div>
                  </div>
                </GlassCard>
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}


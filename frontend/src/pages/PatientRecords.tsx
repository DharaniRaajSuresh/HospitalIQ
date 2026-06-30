import { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, User, ChevronRight, Columns, List, ArrowUpDown, ChevronLeft, ChevronRight as ChevronRightIcon } from 'lucide-react';
import { getPatients } from '../api';
import { useDebounce } from '../hooks/useDebounce';

interface Patient {
  id: number;
  patient_name: string;
  age: number;
  blood_group: string;
  gender: string;
  state: string;
  district: string;
  pre_existing_conditions: string;
}

const BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
const GENDERS = ['Male', 'Female', 'Other'];
const AVATAR_COLORS = [
  'from-cyan-500 to-blue-600', 'from-violet-500 to-purple-600', 'from-emerald-500 to-teal-600',
  'from-rose-500 to-pink-600', 'from-amber-500 to-orange-600', 'from-indigo-500 to-blue-600',
  'from-teal-500 to-cyan-600', 'from-fuchsia-500 to-violet-600',
];

function getInitialColor(id: number): string {
  return AVATAR_COLORS[id % AVATAR_COLORS.length];
}

function getInitials(name: string): string {
  if (!name) return '?';
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
}

function getRiskLevel(age: number, conditions: string): { label: string; color: string } {
  const hasConditions = conditions && conditions.trim().length > 0;
  if (age > 65 && hasConditions) return { label: 'High', color: 'text-rose-400' };
  if (age > 60 || hasConditions) return { label: 'Moderate', color: 'text-amber-400' };
  if (age > 45) return { label: 'Watch', color: 'text-cyan-400' };
  return { label: 'Low', color: 'text-emerald-400' };
}

export default function PatientRecords() {
  useEffect(() => { document.title = 'Patient Records | HOSPi'; }, []);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [apiError, setApiError] = useState('');
  const [page, setPage] = useState(1);
  const [viewMode, setViewMode] = useState<'card' | 'table'>(
    (sessionStorage.getItem('patientViewMode') as 'card' | 'table') || 'card'
  );
  const [sortField, setSortField] = useState<string>('');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [filterBlood, setFilterBlood] = useState<string[]>([]);
  const [filterGender, setFilterGender] = useState<string[]>([]);
  const [filterRisk, setFilterRisk] = useState<string[]>([]);
  const perPage = 20;

  const debouncedSearch = useDebounce(search, 300);

  const toggleFilter = (arr: string[], val: string, setter: (v: string[]) => void) => {
    setter(arr.includes(val) ? arr.filter(v => v !== val) : [...arr, val]);
    setPage(1);
  };

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);

  const fetchPatients = async () => {
    setLoading(true);
    setApiError('');
    try {
      const params: Record<string, string> = { limit: String(perPage), skip: String((page - 1) * perPage) };
      if (debouncedSearch) params.search = debouncedSearch;
      const data = await getPatients<Patient>(params);
      setPatients(data.patients || []);
      setTotal(data.total || 0);
    } catch (e: any) {
      setApiError(e?.status || e?.message || String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchPatients(); }, [page, debouncedSearch]);

  const toggleView = (mode: 'card' | 'table') => {
    setViewMode(mode);
    sessionStorage.setItem('patientViewMode', mode);
  };

  const handleSort = (field: string) => {
    if (sortField === field) { setSortDir(d => d === 'asc' ? 'desc' : 'asc'); }
    else { setSortField(field); setSortDir('asc'); }
  };

  const filtered = useMemo(() => {
    let list = [...patients];
    if (filterBlood.length) list = list.filter(p => filterBlood.includes(p.blood_group));
    if (filterGender.length) list = list.filter(p => filterGender.includes(p.gender));
    if (filterRisk.length) {
      list = list.filter(p => filterRisk.includes(getRiskLevel(p.age, p.pre_existing_conditions).label));
    }
    if (sortField) {
      list.sort((a, b) => {
        const va = (a as any)[sortField] || '';
        const vb = (b as any)[sortField] || '';
        const cmp = typeof va === 'number' ? va - vb : String(va).localeCompare(String(vb));
        return sortDir === 'asc' ? cmp : -cmp;
      });
    }
    return list;
  }, [patients, filterBlood, filterGender, filterRisk, sortField, sortDir]);

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Patient Records</h1>
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{total.toLocaleString()} registered patients</p>
        </div>
      </div>

      {/* Search + View Toggle */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          <input type="text" value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search by patient name..."
            className="w-full bg-[var(--color-surface-1)] border border-[var(--color-border-subtle)] rounded-lg py-2.5 pl-10 pr-4 text-sm text-white focus:outline-none focus:border-[var(--color-accent-cyan)] transition-all" />
        </div>
        <div className="flex gap-1 p-0.5 rounded-md bg-[var(--color-surface-2)]">
          <button onClick={() => toggleView('card')}
            className={`p-2 rounded transition-all ${viewMode === 'card' ? 'bg-[var(--color-surface-1)] text-white' : 'text-[var(--color-text-muted)]'}`}>
            <List className="w-4 h-4" />
          </button>
          <button onClick={() => toggleView('table')}
            className={`p-2 rounded transition-all ${viewMode === 'table' ? 'bg-[var(--color-surface-1)] text-white' : 'text-[var(--color-text-muted)]'}`}>
            <Columns className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filter Chips */}
      <div className="flex flex-wrap gap-2">
        {BLOOD_GROUPS.map(bg => (
          <button key={bg} onClick={() => toggleFilter(filterBlood, bg, setFilterBlood)}
            className={`px-2.5 py-1 text-[10px] font-mono rounded-full border transition-all ${filterBlood.includes(bg) ? 'border-[var(--color-accent-cyan)] bg-[var(--color-accent-cyan)]/10 text-[var(--color-accent-cyan)]' : 'border-[var(--color-border-subtle)] text-[var(--color-text-muted)] hover:border-[var(--color-border-strong)]'}`}>
            {bg}
          </button>
        ))}
        <span className="w-px h-5 bg-[var(--color-border-subtle)] self-center" />
        {GENDERS.map(g => (
          <button key={g} onClick={() => toggleFilter(filterGender, g, setFilterGender)}
            className={`px-2.5 py-1 text-[10px] font-mono rounded-full border transition-all ${filterGender.includes(g) ? 'border-[var(--color-accent-violet)] bg-[var(--color-accent-violet)]/10 text-[var(--color-accent-violet)]' : 'border-[var(--color-border-subtle)] text-[var(--color-text-muted)] hover:border-[var(--color-border-strong)]'}`}>
            {g}
          </button>
        ))}
        <span className="w-px h-5 bg-[var(--color-border-subtle)] self-center" />
        {['Low', 'Watch', 'Moderate', 'High'].map(risk => (
          <button key={risk} onClick={() => toggleFilter(filterRisk, risk, setFilterRisk)}
            className={`px-2.5 py-1 text-[10px] font-mono rounded-full border transition-all ${filterRisk.includes(risk) ? 'border-[var(--color-accent-rose)] bg-[var(--color-accent-rose)]/10 text-[var(--color-accent-rose)]' : 'border-[var(--color-border-subtle)] text-[var(--color-text-muted)] hover:border-[var(--color-border-strong)]'}`}>
            {risk}
          </button>
        ))}
      </div>

      {apiError && (
        <div className="p-3 rounded-lg border border-[var(--color-accent-rose)]/30 bg-[var(--color-accent-rose)]/10 text-xs text-[var(--color-accent-rose)]">
          API Error: {apiError}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-[var(--color-accent-cyan)] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <User className="w-10 h-10 text-[var(--color-text-muted)] opacity-30 mb-3" />
          <p className="text-sm text-[var(--color-text-muted)]">No patients found</p>
        </div>
      ) : viewMode === 'card' ? (
        <div className="grid gap-2">
          {filtered.map((p, i) => {
            const risk = getRiskLevel(p.age, p.pre_existing_conditions);
            return (
              <div key={p.id} onClick={() => navigate(`/dashboard/patients/${p.id}`)}
                className="group flex items-center gap-4 p-3 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] hover:bg-[var(--color-surface-2)] hover:border-[var(--color-border-strong)] cursor-pointer transition-all">
                <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${getInitialColor(p.id)} flex items-center justify-center text-sm font-bold text-white flex-shrink-0`}>
                  {getInitials(p.patient_name)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate group-hover:text-[var(--color-accent-cyan)] transition-colors">{p.patient_name}</p>
                  <div className="flex items-center gap-3 text-[10px] text-[var(--color-text-muted)] font-mono mt-0.5">
                    <span>{p.age || '?'} yrs</span>
                    <span>{p.blood_group || 'N/A'}</span>
                    <span>{p.gender || 'N/A'}</span>
                    <span className="truncate">{p.state || 'N/A'}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-[10px] font-mono ${risk.color}`}>{risk.label}</span>
                  {p.pre_existing_conditions && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--color-accent-amber)]/10 text-[var(--color-accent-amber)] border border-[var(--color-accent-amber)]/20">
                      {p.pre_existing_conditions.split(',').length} cond.
                    </span>
                  )}
                  <ChevronRight className="w-4 h-4 text-[var(--color-text-muted)] group-hover:text-[var(--color-accent-cyan)] transition-colors" />
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border-subtle)]">
                  {['patient_name', 'age', 'blood_group', 'gender', 'state', 'risk'].map(field => (
                    <th key={field} onClick={() => field !== 'risk' && handleSort(field)}
                      className={`px-4 py-3 text-[10px] font-mono text-[var(--color-text-muted)] uppercase tracking-wider text-left ${field !== 'risk' ? 'cursor-pointer hover:text-white transition-colors' : ''}`}>
                      <span className="inline-flex items-center gap-1">
                        {field === 'patient_name' ? 'Name' : field}
                        {sortField === field && <ArrowUpDown className={`w-3 h-3 transition-transform ${sortDir === 'desc' ? 'rotate-180' : ''}`} />}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map(p => {
                  const risk = getRiskLevel(p.age, p.pre_existing_conditions);
                  return (
                    <tr key={p.id} onClick={() => navigate(`/dashboard/patients/${p.id}`)}
                      className="border-b border-[var(--color-border-subtle)]/50 hover:bg-[var(--color-surface-2)]/50 cursor-pointer transition-colors last:border-0">
                      <td className="px-4 py-3 text-white">{p.patient_name}</td>
                      <td className="px-4 py-3 text-[var(--color-text-muted)] font-mono">{p.age || '?'}</td>
                      <td className="px-4 py-3 text-[var(--color-text-muted)] font-mono">{p.blood_group || 'N/A'}</td>
                      <td className="px-4 py-3 text-[var(--color-text-muted)]">{p.gender || 'N/A'}</td>
                      <td className="px-4 py-3 text-[var(--color-text-muted)]">{p.state || 'N/A'}</td>
                      <td className="px-4 py-3"><span className={`text-[10px] font-mono ${risk.color}`}>{risk.label}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)]">
          <span className="font-mono">{total.toLocaleString()} total patients</span>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
              className="p-1.5 rounded hover:bg-[var(--color-surface-2)] disabled:opacity-30 transition-colors">
              <ChevronLeft className="w-4 h-4" />
            </button>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const start = Math.max(1, Math.min(page - 2, totalPages - 4));
              const num = start + i;
              return (
                <button key={num} onClick={() => setPage(num)}
                  className={`px-2.5 py-1 rounded font-mono transition-all ${page === num ? 'bg-[var(--color-accent-cyan)] text-black' : 'hover:bg-[var(--color-surface-2)]'}`}>
                  {num}
                </button>
              );
            })}
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
              className="p-1.5 rounded hover:bg-[var(--color-surface-2)] disabled:opacity-30 transition-colors">
              <ChevronRightIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

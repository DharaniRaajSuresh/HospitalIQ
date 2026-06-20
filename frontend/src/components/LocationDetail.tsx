import { useState, useEffect } from 'react';
import { getLocationStats, getDistrictList, getLocalities } from '../api';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, CartesianGrid
} from 'recharts';

const COLORS = ['#4f8cff','#00cc64','#f5a623','#ff6633','#a855f7','#06b6d4','#ec4899','#f97316'];

export default function LocationDetail({ state, onBack }) {
  const [view, setView] = useState('overview');
  const [selectedDistrict, setSelectedDistrict] = useState(null);
  const [selectedLocality, setSelectedLocality] = useState(null);
  const [data, setData] = useState(null);
  const [districts, setDistricts] = useState([]);
  const [localities, setLocalities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!state) return;
    setLoading(true);
    setError(null);
    setView('overview');
    setSelectedDistrict(null);
    setSelectedLocality(null);
    Promise.all([
      getLocationStats(state),
      getDistrictList(state)
    ])
    .then(([s, d]: [any, any]) => { setData(s); setDistricts(d); })
    .catch((e: any) => setError(e.message))
    .finally(() => setLoading(false));
  }, [state]);

  function showDistrict(district) {
    setSelectedDistrict(district);
    setSelectedLocality(null);
    setView('district');
    setLoading(true);
    Promise.all([
      getLocationStats(null, district),
      getLocalities(district)
    ])
    .then(([s, l]: [any, any]) => { setData(s); setLocalities(l); })
    .catch((e: any) => setError(e.message))
    .finally(() => setLoading(false));
  }

  function showLocality(locality) {
    setSelectedLocality(locality);
    setView('locality');
  }

  function goBack() {
    if (view === 'locality') {
      setView('district');
      setSelectedLocality(null);
    } else if (view === 'district') {
      setView('overview');
      setSelectedDistrict(null);
      setLoading(true);
      Promise.all([
        getLocationStats(state),
        getDistrictList(state)
      ])
      .then(([s, d]: [any, any]) => { setData(s); setDistricts(d); })
      .catch((e: any) => setError(e.message))
      .finally(() => setLoading(false));
    }
  }

  if (!state) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: 48 }}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 40, height: 40, color: '#5c6078', marginBottom: 12, opacity: 0.5 }}>
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
        </svg>
        <p style={{ color: '#5c6078', fontSize: 14, fontWeight: 500 }}>Click a state on the map</p>
      </div>
    );
  }

  if (loading && !data) return <div className="card"><div className="loading">Loading...</div></div>;
  if (error) return <div className="card"><div className="error">{error}</div></div>;

  const breadcrumb = (
    <div style={{ fontSize: 12, color: '#5c6078', marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
      <span style={{ cursor: 'pointer', color: '#4f8cff', fontWeight: 500 }} onClick={goBack}>{state}</span>
      {view !== 'overview' && <span style={{ color: '#5c6078' }}>/</span>}
      {view === 'district' && <span style={{ cursor: 'pointer', color: '#4f8cff', fontWeight: 500 }} onClick={goBack}>{selectedDistrict}</span>}
      {view === 'locality' && <span style={{ cursor: 'pointer', color: '#4f8cff', fontWeight: 500 }} onClick={goBack}>{selectedDistrict}</span>}
      {view === 'locality' && <span style={{ color: '#5c6078' }}>/</span>}
      {view === 'locality' && <span style={{ color: '#9498b0' }}>{selectedLocality}</span>}
    </div>
  );

  if (view === 'overview') {
    const h = data?.hospitals || {};
    const m = data?.mortality || {};
    const b = data?.beds || {};

    const chartData = districts.slice(0, 20).map(d => ({
      name: d.district.length > 10 ? d.district.slice(0, 10) + '..' : d.district,
      fullName: d.district,
      score: d.avg_score,
    }));

    const causeData = (m.common_causes || []).map(c => ({ name: c.cause, deaths: c.deaths }));

    return (
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
          <div>
            <div className="card-title" style={{ marginBottom: 4 }}>State Overview</div>
            <h3 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.3px' }}>{state}</h3>
          </div>
          <button
            onClick={onBack}
            style={{
              background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border)',
              borderRadius: 8, color: '#9498b0', cursor: 'pointer',
              width: 32, height: 32, display: 'flex', alignItems: 'center',
              justifyContent: 'center', fontSize: 16, transition: 'all 0.15s'
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; e.currentTarget.style.color = '#f0f2f8'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = '#9498b0'; }}
          >✕</button>
        </div>

        <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 12 }}>
          <StatBox value={h.total || 0} label="Hospitals" color="#4f8cff" />
          <StatBox value={h.total_beds?.toLocaleString() || 0} label="Beds" color="#00cc64" />
          <StatBox value={`${h.fatality_rate || 0}%`} label="Fatality" color="#ff6633" />
        </div>
        <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 16 }}>
          <StatBox value={h.avg_score || 0} label="Avg Score" color="#f5a623" />
          <StatBox value={m.avg_death_rate || 0} label="Death Rate" color="#a855f7" />
          <StatBox value={`${b.avg_occupancy || 0}%`} label="Occupancy" color="#06b6d4" />
        </div>

        {h.best_hospital && (
          <div style={{
            background: 'linear-gradient(135deg, rgba(79,140,255,0.06), rgba(124,92,255,0.06))',
            border: '1px solid rgba(79,140,255,0.1)', borderRadius: 10, padding: 16, marginBottom: 16
          }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: '#5c6078', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>Best Hospital</div>
            <div style={{ fontSize: 15, fontWeight: 600 }}>{h.best_hospital.name}</div>
            <div style={{ fontSize: 12, color: '#9498b0', marginTop: 2 }}>{h.best_hospital.type} &middot; Score: {h.best_hospital.score}</div>
          </div>
        )}

        {chartData.length > 0 && (
          <>
            <div className="card-title" style={{ marginBottom: 12 }}>District Hospital Scores</div>
            <div style={{ height: 180, marginBottom: 16 }}>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={chartData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis type="number" stroke="#5c6078" fontSize={10} axisLine={false} tickLine={false} />
                  <YAxis dataKey="name" type="category" stroke="#5c6078" fontSize={9} width={70} axisLine={false} tickLine={false} />
                  <Tooltip
                    formatter={(v, n, p) => [v, p.payload.fullName]}
                    contentStyle={{ background: '#1c1f30', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.4)' }}
                    labelStyle={{ color: '#f0f2f8' }}
                  />
                  <Bar dataKey="score" fill="#4f8cff" radius={[0, 4, 4, 0]} name="Score" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        )}

        {districts.length > 0 && (
          <>
            <div className="card-title" style={{ marginBottom: 8 }}>All Districts</div>
            <div className="table-container" style={{ maxHeight: 240, overflowY: 'auto' }}>
              <table style={{ fontSize: 12 }}>
                <thead>
                  <tr>
                    <th>District</th>
                    <th>Hosp</th>
                    <th>Beds</th>
                    <th>Score</th>
                    <th>Death Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {districts.map((d, i) => (
                    <tr key={d.district} onClick={() => showDistrict(d.district)}
                      style={{ cursor: 'pointer' }}>
                      <td style={{ fontWeight: 500, color: '#f0f2f8' }}>{d.district}</td>
                      <td>{d.hospitals}</td>
                      <td>{d.total_beds}</td>
                      <td style={{ color: '#4f8cff', fontWeight: 600 }}>{d.avg_score}</td>
                      <td>{d.avg_death_rate}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {causeData.length > 0 && (
          <>
            <div className="card-title" style={{ marginTop: 16, marginBottom: 8 }}>Causes of Death</div>
            <div style={{ height: 150 }}>
              <ResponsiveContainer width="100%" height={150}>
                <PieChart>
                  <Pie data={causeData} cx="50%" cy="50%" outerRadius={55}
                    dataKey="deaths" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                    {causeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#1c1f30', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </div>
    );
  }

  if (view === 'district') {
    const h = data?.hospitals || {};
    const m = data?.mortality || {};

    const causeData = (m.common_causes || []).map(c => ({ name: c.cause, deaths: c.deaths }));

    return (
      <div className="card">
        {breadcrumb}
        <div className="card-title" style={{ marginBottom: 4 }}>District Overview</div>
        <h3 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.3px', marginBottom: 16 }}>{selectedDistrict}</h3>

        <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 12 }}>
          <StatBox value={h.total || 0} label="Hospitals" color="#4f8cff" />
          <StatBox value={h.total_beds || 0} label="Beds" color="#00cc64" />
          <StatBox value={`${h.fatality_rate || 0}%`} label="Fatality" color="#ff6633" />
        </div>

        {h.best_hospital && (
          <div style={{
            background: 'linear-gradient(135deg, rgba(79,140,255,0.06), rgba(124,92,255,0.06))',
            border: '1px solid rgba(79,140,255,0.1)', borderRadius: 10, padding: 16, marginBottom: 16
          }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: '#5c6078', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>Best Hospital</div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{h.best_hospital.name}</div>
            <div style={{ fontSize: 12, color: '#9498b0', marginTop: 2 }}>Score: {h.best_hospital.score} &middot; Success: {h.best_hospital.success_rate}%</div>
          </div>
        )}

        {localities.length > 0 && (
          <>
            <div className="card-title" style={{ marginBottom: 8 }}>Localities / Areas</div>
            <div className="table-container" style={{ maxHeight: 240, overflowY: 'auto' }}>
              <table style={{ fontSize: 12 }}>
                <thead>
                  <tr>
                    <th>Area</th>
                    <th>Hosp</th>
                    <th>Beds</th>
                    <th>Score</th>
                    <th>Death Rate</th>
                    <th>Occupancy</th>
                  </tr>
                </thead>
                <tbody>
                  {localities.map(l => (
                    <tr key={l.locality} onClick={() => showLocality(l)}
                      style={{ cursor: 'pointer' }}>
                      <td style={{ fontWeight: 500, color: '#f0f2f8' }}>{l.locality}</td>
                      <td>{l.hospitals}</td>
                      <td>{l.estimated_beds}</td>
                      <td style={{ color: '#4f8cff', fontWeight: 600 }}>{l.score}</td>
                      <td>{l.death_rate}</td>
                      <td>{l.bed_occupancy}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="card-title" style={{ marginTop: 16, marginBottom: 8 }}>Locality Scores</div>
            <div style={{ height: 150 }}>
              <ResponsiveContainer width="100%" height={150}>
                <BarChart data={localities} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis type="number" stroke="#5c6078" fontSize={10} axisLine={false} tickLine={false} />
                  <YAxis dataKey="locality" type="category" stroke="#5c6078" fontSize={9} width={80} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: '#1c1f30', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="score" fill="#4f8cff" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        )}

        {causeData.length > 0 && (
          <>
            <div className="card-title" style={{ marginTop: 16, marginBottom: 8 }}>Causes of Death</div>
            <div style={{ height: 150 }}>
              <ResponsiveContainer width="100%" height={150}>
                <PieChart>
                  <Pie data={causeData} cx="50%" cy="50%" outerRadius={55}
                    dataKey="deaths" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                    {causeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#1c1f30', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </div>
    );
  }

  if (view === 'locality' && selectedLocality) {
    return (
      <div className="card">
        {breadcrumb}
        <div className="card-title" style={{ marginBottom: 4 }}>Locality Overview</div>
        <h3 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.3px', marginBottom: 16 }}>{selectedLocality.locality}</h3>

        <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)', marginBottom: 12 }}>
          <StatBox value={selectedLocality.hospitals || 0} label="Hospitals" color="#4f8cff" />
          <StatBox value={selectedLocality.estimated_beds || 0} label="Est. Beds" color="#00cc64" />
        </div>
        <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)', marginBottom: 12 }}>
          <StatBox value={selectedLocality.score || 0} label="Score" color="#f5a623" />
          <StatBox value={`${selectedLocality.bed_occupancy || 0}%`} label="Occupancy" color="#06b6d4" />
        </div>
        <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
          <StatBox value={selectedLocality.death_rate || 0} label="Death Rate" color="#ff6633" />
          <StatBox value={(selectedLocality.population_served || 0).toLocaleString()} label="Population" color="#a855f7" />
        </div>
      </div>
    );
  }

  return null;
}

function StatBox({ value, label, color }) {
  return (
    <div className="stat-card" style={{ padding: 14 }}>
      <div className="stat-number" style={{ fontSize: 24, color }}>{value}</div>
      <div className="stat-label" style={{ fontSize: 10 }}>{label}</div>
    </div>
  );
}


import { useState, useEffect, useCallback } from 'react';
import { MapContainer, TileLayer, useMap, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { getLocationStats } from '../api';

const STATE_COORDS = {
  'Andhra Pradesh': [15.9, 79.9], 'Arunachal Pradesh': [27.1, 93.6], 'Assam': [26.2, 92.9],
  'Bihar': [25.1, 85.3], 'Chhattisgarh': [21.3, 81.9], 'Delhi': [28.7, 77.1],
  'Goa': [15.5, 73.9], 'Gujarat': [22.3, 71.2], 'Haryana': [29.1, 76.0],
  'Himachal Pradesh': [31.1, 77.2], 'Jammu and Kashmir': [33.8, 76.8],
  'Jharkhand': [23.6, 85.1], 'Karnataka': [15.3, 75.7], 'Kerala': [10.5, 76.3],
  'Madhya Pradesh': [23.5, 78.5], 'Maharashtra': [19.8, 76.7],
  'Manipur': [24.8, 93.7], 'Meghalaya': [25.6, 91.5], 'Mizoram': [23.2, 92.9],
  'Nagaland': [26.1, 94.5], 'Odisha': [20.5, 84.7], 'Punjab': [30.9, 75.3],
  'Rajasthan': [27.0, 74.2], 'Sikkim': [27.5, 88.5], 'Tamil Nadu': [11.1, 78.4],
  'Telangana': [17.6, 79.6], 'Tripura': [23.8, 91.5], 'Uttar Pradesh': [27.2, 80.5],
  'Uttarakhand': [30.1, 78.9], 'West Bengal': [23.0, 87.5],
};

const ALL_LOCATIONS = Object.keys(STATE_COORDS);

function FlyTo({ coords }) {
  const map = useMap();
  useEffect(() => {
    if (coords) map.flyTo(coords, 7, { duration: 1.5 });
  }, [coords, map]);
  return null;
}

function formatNum(n) {
  if (n == null) return '—';
  if (n >= 1e7) return (n / 1e7).toFixed(1) + 'Cr';
  if (n >= 1e5) return (n / 1e5).toFixed(1) + 'L';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return n.toLocaleString();
}

export default function RegionalMap() {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [mapCoords, setMapCoords] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleInput = useCallback((val) => {
    setQuery(val);
    const q = val.toLowerCase();
    const matches = q ? ALL_LOCATIONS.filter((s) => s.toLowerCase().includes(q)) : ALL_LOCATIONS;
    setSuggestions(matches);
  }, []);

  const handleSelect = useCallback(async (location) => {
    setSelectedLocation(location);
    setQuery(location);
    setSuggestions([]);
    setMapCoords(STATE_COORDS[location]);

    setLoading(true);
    try {
      const d = await getLocationStats(location, '');
      setStats(d);
    } catch {
      setStats(null);
    }
    setLoading(false);
  }, []);

  return (
    <div className="region-map relative w-full" style={{ height: 'calc(100vh - 8rem)' }}>
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] w-full max-w-lg">
        <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => handleInput(e.target.value)}
              onFocus={() => { if (!query) setSuggestions(ALL_LOCATIONS); }}
              placeholder="Search for a state..."
              className="w-full px-4 py-3 rounded-xl bg-[#0f172a]/95 backdrop-blur border border-gray-700 shadow-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 text-base"
            />
            {suggestions.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-[#0f172a] rounded-xl shadow-2xl border border-gray-700 overflow-y-auto max-h-80" style={{ zIndex: 10000 }}>
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => { handleSelect(s); }}
                    className="w-full px-4 py-2.5 text-left text-gray-200 hover:bg-[#1e293b] hover:text-white transition-colors text-sm border-b border-gray-800 last:border-0"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
        </div>
      </div>

      <div className="flex h-full gap-4 pt-16">
        <div className="flex-1 rounded-2xl border border-gray-700 shadow-2xl overflow-hidden">
          <MapContainer center={[20.6, 79.0]} zoom={5}
            style={{ height: '100%', width: '100%', background: '#0f172a' }}>
            <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>' />
            <FlyTo coords={mapCoords} />
            {mapCoords && (
              <Marker position={mapCoords} icon={L.divIcon({ className: '', html: '<div style="background:#3b82f6;width:16px;height:16px;border-radius:50%;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3)"></div>' })}>
                <Popup>{selectedLocation}</Popup>
              </Marker>
            )}
          </MapContainer>
        </div>

        <div className={`w-96 flex-shrink-0 transition-all duration-300 ${stats ? 'opacity-100' : 'opacity-0 pointer-events-none w-0'}`}>
          {stats && (
            <div className="h-full rounded-2xl border border-gray-200 bg-[#0f172a] shadow-lg overflow-y-auto">
              <div className="sticky top-0 bg-[#0f172a] border-b border-gray-700 p-4">
                <h2 className="text-lg font-bold text-white">{stats.state}</h2>
                {stats.district && <p className="text-sm text-gray-400">{stats.district}</p>}
              </div>

              <div className="p-4 space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <MetricCard label="Population" value={formatNum(stats.mortality?.total_population)} />
                  <MetricCard label="Avg Death Rate" value={stats.mortality?.avg_death_rate + '%'} />
                  <MetricCard label="Total Deaths" value={formatNum(stats.mortality?.total_deaths)} />
                </div>

                {stats.hospitals && (
                  <Section title="Hospitals">
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <StatRow label="Total" value={stats.hospitals.total} />
                      <StatRow label="Total Beds" value={stats.hospitals.total_beds} />
                      <StatRow label="Avg Success Rate" value={stats.hospitals.avg_success_rate + '%'} />
                      <StatRow label="Avg Score" value={stats.hospitals.avg_score} />
                      <StatRow label="Fatality Rate" value={stats.hospitals.fatality_rate + '%'} />
                    </div>
                    {stats.hospitals.best_hospital && (
                      <div className="mt-2 p-2 bg-[#1e293b] rounded-lg">
                        <p className="text-xs text-gray-400 mb-1">Best Hospital</p>
                        <p className="text-sm font-medium text-white">{stats.hospitals.best_hospital.name}</p>
                        <p className="text-xs text-gray-400">
                          {stats.hospitals.best_hospital.district} &middot; {stats.hospitals.best_hospital.type} &middot; Score: {stats.hospitals.best_hospital.score}
                        </p>
                      </div>
                    )}
                  </Section>
                )}

                {stats.mortality?.common_causes?.length > 0 && (
                  <Section title="Top Causes of Death">
                    <div className="space-y-1">
                      {stats.mortality.common_causes.map((c, i) => (
                        <div key={i} className="flex justify-between text-sm">
                          <span className="text-gray-300">{c.cause}</span>
                          <span className="text-gray-400">{formatNum(c.deaths)}</span>
                        </div>
                      ))}
                    </div>
                  </Section>
                )}

                {stats.beds && (
                  <Section title="Bed Occupancy">
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <StatRow label="Total Beds" value={stats.beds.total_beds} />
                      <StatRow label="Avg Occupancy" value={stats.beds.avg_occupancy + '%'} />
                    </div>
                  </Section>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value }) {
  return (
    <div className="bg-[#1e293b] rounded-lg p-3">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className="text-lg font-semibold text-white">{value ?? '—'}</p>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="bg-[#1e293b] rounded-lg p-3">
      <h3 className="text-sm font-semibold text-gray-200 mb-2">{title}</h3>
      {children}
    </div>
  );
}

function StatRow({ label, value }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-400">{label}</span>
      <span className="text-gray-200 font-medium">{value ?? '—'}</span>
    </div>
  );
}


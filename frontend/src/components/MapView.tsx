// @ts-nocheck
import { useState, useEffect, useRef, useCallback } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix leaflet default icon paths (missing in webpack/vite)
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

function FitBounds({ data }) {
  const map = useMap();
  useEffect(() => {
    if (data) {
      const layer = L.geoJSON(data);
      map.fitBounds(layer.getBounds().pad(0.1));
    }
  }, [data, map]);
  return null;
}

function StateLayer({ geoData, selectedState, onSelect }) {
  const map = useMap();
  const layerRef = useRef(null);
  const geoJsonRef = useRef(null);

  useEffect(() => {
    if (!geoData || !map) return;
    if (geoJsonRef.current) {
      map.removeLayer(geoJsonRef.current);
    }

    function getStateName(props) {
      return props?.NAME_1 || props?.name || '';
    }

    const geoLayer = L.geoJSON(geoData, {
      style: () => ({
        fillColor: '#1a1d27',
        weight: 1,
        opacity: 1,
        color: '#4f8cff',
        fillOpacity: 0.4,
      }),
      onEachFeature: (feature, layer) => {
        const name = getStateName(feature.properties);
        layer.bindTooltip(name, { sticky: true, className: 'state-tooltip' });
        layer.stateName = name;

        layer.on({
          click: () => {
            if (onSelect) onSelect(name);
          },
          mouseover: (e) => {
            const l = e.target;
            l.setStyle({ fillOpacity: 0.6, weight: 2 });
          },
          mouseout: (e) => {
            const l = e.target;
            if (l.stateName === selectedState) {
              l.setStyle({ fillOpacity: 0.7, weight: 2 });
            } else {
              l.setStyle({ fillOpacity: 0.4, weight: 1 });
            }
          },
        });
      },
    });

    geoLayer.addTo(map);
    geoJsonRef.current = geoLayer;
    layerRef.current = geoLayer;

    return () => {
      if (geoJsonRef.current) {
        map.removeLayer(geoJsonRef.current);
      }
    };
  }, [geoData, map]);

  // Update selection highlighting when selectedState changes
  useEffect(() => {
    if (!geoJsonRef.current) return;
    geoJsonRef.current.eachLayer((layer) => {
      if (layer.stateName === selectedState) {
        layer.setStyle({ fillColor: '#4f8cff', fillOpacity: 0.7, weight: 2 });
      } else {
        layer.setStyle({ fillColor: '#1a1d27', fillOpacity: 0.4, weight: 1 });
      }
    });
  }, [selectedState]);

  return null;
}

export default function MapView({ onSelectState }) {
  const [geoData, setGeoData] = useState(null);
  const [selectedState, setSelectedState] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check cache first
    const cached = localStorage.getItem('statesGeoData');
    const cacheTime = localStorage.getItem('statesGeoDataTime');
    const now = Date.now();
    const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours

    if (cached && cacheTime && (now - parseInt(cacheTime)) < CACHE_DURATION) {
      try {
        setGeoData(JSON.parse(cached));
        setIsLoading(false);
        return;
      } catch (e) {
        console.error('Error parsing cached geo data:', e);
      }
    }

    // Fetch from server if not cached or cache expired
    fetch('/states.json')
      .then(r => r.json())
      .then(data => {
        setGeoData(data);
        // Cache the data
        try {
          localStorage.setItem('statesGeoData', JSON.stringify(data));
          localStorage.setItem('statesGeoDataTime', now.toString());
        } catch (e) {
          console.error('Error caching geo data:', e);
        }
      })
      .catch(e => console.warn('Failed to load map data:', e))
      .finally(() => setIsLoading(false));
  }, []);

  const handleSelect = useCallback((name) => {
    setSelectedState(name);
    if (onSelectState) onSelectState(name);
  }, [onSelectState]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="w-8 h-8 border-3 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
          <p className="text-cyan-400 text-sm">Loading map data...</p>
        </div>
      </div>
    );
  }

  if (!geoData) return <div className="text-red-400 p-4">Failed to load map data</div>;

  return (
    <div style={{ height: 'calc(100vh - 200px)', width: '100%', borderRadius: 12, overflow: 'hidden' }}>
      <MapContainer
        center={[20.5937, 78.9629]}
        zoom={5}
        style={{ height: '100%', width: '100%' }}
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds data={geoData} />
        <StateLayer
          geoData={geoData}
          selectedState={selectedState}
          onSelect={handleSelect}
        />
      </MapContainer>
    </div>
  );
}


import React, { useEffect, useState, lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { isAuthenticated, login } from './api';

import DashboardLayout from './layouts/DashboardLayout';

import AmbientBackground from './components/ui/AmbientBackground';

const LandingPage = lazy(() => import('./pages/LandingPage'));
const CommandCenter = lazy(() => import('./pages/CommandCenter'));
const BedForecast = lazy(() => import('./pages/ForecastingCenter'));
const MortalityPredictor = lazy(() => import('./pages/MortalityAnalytics'));
const HospitalRankings = lazy(() => import('./pages/HospitalRankingsPage'));
const IndiaMap = lazy(() => import('./pages/IntelligenceMap'));
const RegionalMap = lazy(() => import('./pages/RegionalMap'));
const Analytics = lazy(() => import('./pages/AnalyticsDashboard'));
const AssistantChatbot = lazy(() => import('./pages/AssistantChatbot'));
const PandemicScenario = lazy(() => import('./pages/PandemicScenario'));
const PatientRecords = lazy(() => import('./pages/PatientRecords'));
const PatientDetail = lazy(() => import('./pages/PatientDetail'));

const FloatingCopilot = lazy(() => import('./components/FloatingCopilot'));

const PageLoader: React.FC = () => (
  <div className="min-h-screen bg-[#030712] flex items-center justify-center relative overflow-hidden">
    <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(0,240,255,0.15),transparent_50%)]"></div>
    <div className="flex flex-col items-center z-10">
      <div className="w-10 h-10 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin shadow-[0_0_15px_rgba(0,240,255,0.5)]"></div>
      <p className="mt-4 text-cyan-400 text-sm animate-pulse tracking-[2px] uppercase font-bold">Initializing Systems...</p>
    </div>
  </div>
);

export default function App(): React.ReactElement {
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let mounted = true;
    const timeout = setTimeout(() => { if (mounted) setIsReady(true); }, 5000);

    async function checkAndLogin(): Promise<void> {
      try {
        const authed = await isAuthenticated();
        if (!authed && mounted && import.meta.env.VITE_DEMO_EMAIL && import.meta.env.VITE_DEMO_PASSWORD) {
          await login(import.meta.env.VITE_DEMO_EMAIL as string, import.meta.env.VITE_DEMO_PASSWORD as string);
        }
      } catch (err) {
        console.error('Silent login failed:', err);
      } finally {
        clearTimeout(timeout);
        if (mounted) setIsReady(true);
      }
    }

    checkAndLogin();

    return () => { mounted = false; clearTimeout(timeout); };
  }, []);

  if (!isReady) {
    return <PageLoader />;
  }

  return (
    <BrowserRouter>
      <AmbientBackground />
      <Suspense fallback={<PageLoader />}>
        <AnimatePresence mode="wait">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/dashboard" element={<DashboardLayout />}>
              <Route index element={<CommandCenter />} />
              <Route path="beds" element={<BedForecast />} />
              <Route path="mortality" element={<MortalityPredictor />} />
              <Route path="hospitals" element={<HospitalRankings />} />
              <Route path="map" element={<IndiaMap />} />
              <Route path="region-map" element={<RegionalMap />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="ai" element={<AssistantChatbot />} />
              <Route path="pandemic" element={<PandemicScenario />} />
              <Route path="patients" element={<PatientRecords />} />
              <Route path="patients/:id" element={<PatientDetail />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AnimatePresence>
        <FloatingCopilot />
      </Suspense>
    </BrowserRouter>
  );
}

import { useEffect, useState, lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { isAuthenticated } from './api';
import DashboardLayout from './layouts/DashboardLayout';
import AmbientBackground from './components/ui/AmbientBackground';
import { ErrorBoundary } from './components/ui/ErrorBoundary';
import { ToastProvider } from './context/ToastContext';
import { LoadingBarProvider } from './context/LoadingBarContext';

const LandingPage = lazy(() => import('./pages/LandingPage'));
const GovLandingPage = lazy(() => import('./pages/GovLandingPage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
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

const PageLoader: React.FC = () => (
  <div className="min-h-screen bg-[#030712] flex items-center justify-center relative overflow-hidden">
    <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(0,240,255,0.15),transparent_50%)]" />
    <div className="flex flex-col items-center z-10">
      <div className="w-10 h-10 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin shadow-[0_0_15px_rgba(0,240,255,0.5)]" />
      <p className="mt-4 text-cyan-400 text-sm animate-pulse tracking-[2px] uppercase font-bold">Initializing Systems...</p>
    </div>
  </div>
);

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const [authed, setAuthed] = useState<boolean | null>(null);
  const location = useLocation();

  useEffect(() => {
    isAuthenticated().then(setAuthed).catch(() => setAuthed(false));
  }, []);

  if (authed === null) return <PageLoader />;
  if (!authed) return <Navigate to="/login" state={{ from: location }} replace />;
  return <>{children}</>;
}

function AppContent() {
  const [isReady, setIsReady] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setTimeout(() => setIsReady(true), 800);
    return () => clearTimeout(timer);
  }, []);

  // Listen for auth:logout events (dispatched by api.ts on 401)
  useEffect(() => {
    const handleLogout = () => {
      window.__auth_token = undefined;
      navigate('/');
    };
    window.addEventListener('auth:logout', handleLogout);
    return () => window.removeEventListener('auth:logout', handleLogout);
  }, [navigate]);

  if (!isReady) return <PageLoader />;

  return (
    <>
      <AmbientBackground />
      <Suspense fallback={<PageLoader />}>
        <AnimatePresence mode="wait">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/gov" element={<GovLandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/dashboard" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
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
      </Suspense>
    </>
  );
}

export default function App(): React.ReactElement {
  return (
    <BrowserRouter>
      <ErrorBoundary>
      <ToastProvider>
        <LoadingBarProvider>
          <AppContent />
        </LoadingBarProvider>
      </ToastProvider>
      </ErrorBoundary>
    </BrowserRouter>
  );
}

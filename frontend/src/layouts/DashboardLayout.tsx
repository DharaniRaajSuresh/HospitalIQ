import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  LayoutDashboard, 
  Map, 
  Globe,
  TrendingUp, 
  Activity, 
  Award, 
  MessageSquare, 
  BarChart2, 
  ShieldAlert,
  Users,
  Menu,
  Search,
  Bell,
  LogOut,
  Settings,
  Lock,
  Hospital,
  User,
  ExternalLink,
  Code2,
  Phone,
  Mail,
  MessageCircle
} from 'lucide-react';
import { getMe, globalSearch, logout, setPassword } from '../api';
import { useDebounce } from '../hooks/useDebounce';
import PageTransition from '../components/ui/PageTransition';
import FloatingParticles from '../components/ui/FloatingParticles';

const navItems = [
  { name: 'Command Center', path: '/dashboard', icon: LayoutDashboard },
  { name: 'District Intelligence', path: '/dashboard/map', icon: Map },
  { name: 'Region Map', path: '/dashboard/region-map', icon: Globe },
  { name: 'Forecasting', path: '/dashboard/beds', icon: TrendingUp },
  { name: 'Mortality Analytics', path: '/dashboard/mortality', icon: Activity },
  { name: 'Rankings', path: '/dashboard/hospitals', icon: Award },
  { name: 'Analytics', path: '/dashboard/analytics', icon: BarChart2 },
  { name: 'Assistant Chatbot', path: '/dashboard/ai', icon: MessageSquare },
  { name: 'Pandemic Simulator', path: '/dashboard/pandemic', icon: ShieldAlert },
  { name: 'Patient Records', path: '/dashboard/patients', icon: Users },
];

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [showSetPw, setShowSetPw] = useState(false);
  const [newPw, setNewPw] = useState('');
  const [pwMsg, setPwMsg] = useState('');
  const [userInfo, setUserInfo] = useState<{ name: string; role: string; initials: string } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<{ patients: { id: number; name: string; state: string; district: string }[]; hospitals: { id: string; name: string; state: string; district: string }[] } | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searching, setSearching] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const debouncedSearch = useDebounce(searchQuery, 300);
  const settingsRef = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (!debouncedSearch.trim()) { setSearchResults(null); setSearchOpen(false); return; }
    let cancelled = false;
    setSearching(true);
    globalSearch<{ patients: { id: number; name: string; state: string; district: string }[]; hospitals: { id: string; name: string; state: string; district: string }[] }>(debouncedSearch.trim())
      .then(data => { if (!cancelled) { setSearchResults(data); setSearchOpen(true); } })
      .catch(() => { if (!cancelled) { setSearchResults(null); setSearchOpen(false); } })
      .finally(() => { if (!cancelled) setSearching(false); });
    return () => { cancelled = true; };
  }, [debouncedSearch]);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && searchQuery.trim()) {
      setSearchOpen(false);
      navigate(`/dashboard/patients?search=${encodeURIComponent(searchQuery.trim())}`);
    }
    if (e.key === 'Escape') {
      setSearchOpen(false);
      (e.target as HTMLInputElement).blur();
    }
  };

  const handleSearchFocus = () => {
    if (searchResults && (searchResults.patients.length > 0 || searchResults.hospitals.length > 0)) {
      setSearchOpen(true);
    }
  };

  useEffect(() => {
    getMe().then((data: Record<string, unknown>) => {
      if (data.authenticated) {
        const name = (data.name as string) || (data.email as string) || 'User';
        setUserInfo({
          name,
          role: (data.role as string) || 'Viewer',
          initials: name.split(' ').map((s: string) => s[0]).join('').slice(0, 2).toUpperCase(),
        });
      }
    }).catch(() => {});
  }, []);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setSettingsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleLogout = async () => {
    setSettingsOpen(false);
    await logout();
    navigate('/login', { replace: true });
  };

  const handleMouseMove = (e) => {
    document.documentElement.style.setProperty('--mouse-x', `${e.clientX}px`);
    document.documentElement.style.setProperty('--mouse-y', `${e.clientY}px`);
  };

  return (
    <div 
      className="min-h-screen bg-[var(--color-bg-primary)] text-[var(--color-text-primary)] flex overflow-hidden font-sans relative"
      onMouseMove={handleMouseMove}
    >
      <FloatingParticles count={30} color="rgba(16, 185, 129, 0.3)" />
      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.aside
        className={`fixed inset-y-0 left-0 z-50 w-64 glass border-r border-[var(--color-border)] flex flex-col transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:flex-shrink-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="h-16 flex items-center px-6 border-b border-[var(--color-border)]">
          <Activity className="w-6 h-6 text-[var(--color-accent-cyan)] mr-2" />
          <span className="text-xl font-bold gradient-text">HospitalIQ</span>
        </div>

        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = item.path === '/dashboard'
              ? location.pathname === '/dashboard'
              : location.pathname.startsWith(item.path);
            const Icon = item.icon;
            
            return (
              <Link
                key={item.name}
                to={item.path}
                className={`flex items-center px-3 py-3 rounded-xl transition-all duration-300 group relative overflow-hidden ${
                  isActive 
                    ? 'text-white bg-[rgba(255,255,255,0.08)] shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]' 
                    : 'text-[var(--color-text-secondary)] hover:text-white hover:bg-[rgba(255,255,255,0.04)]'
                }`}
                onClick={() => setSidebarOpen(false)}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute left-0 inset-y-2 w-1 rounded-r-full bg-gradient-to-b from-[var(--color-accent-cyan)] to-[var(--color-accent-violet)]"
                    initial={false}
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
                <Icon className={`w-5 h-5 ml-2 mr-3 relative z-10 transition-transform duration-300 ${isActive ? 'text-[var(--color-accent-cyan)] scale-110' : 'group-hover:text-white group-hover:scale-110'}`} />
                <span className="font-medium relative z-10 tracking-wide text-sm">{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </motion.aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Header */}
        <header className="h-16 glass border-b border-[var(--color-border)] flex items-center justify-between px-4 sm:px-6 z-30">
          <div className="flex items-center">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 mr-3 rounded-md text-[var(--color-text-secondary)] hover:text-white hover:bg-[var(--color-bg-elevated)] lg:hidden"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="hidden sm:flex items-center text-sm text-[var(--color-text-muted)]">
              <span className="hover:text-white cursor-pointer transition-colors">HospitalIQ</span>
              <span className="mx-2">/</span>
              <span className="text-[var(--color-text-primary)]">
                {navItems.find(item => item.path === location.pathname)?.name || 'Dashboard'}
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-3 sm:space-x-4">

            <div ref={searchRef} className="relative hidden md:block w-72 group">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] group-focus-within:text-[var(--color-accent-cyan)] transition-colors" />
              <input 
                type="text" 
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                onKeyDown={handleSearchKeyDown}
                onFocus={handleSearchFocus}
                placeholder="Search resources, records..." 
                className="bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.08)] text-[var(--color-text-primary)] text-sm rounded-full pl-10 pr-4 py-2 focus:outline-none focus:border-[var(--color-accent-cyan)] focus:bg-[rgba(255,255,255,0.05)] focus:shadow-[0_0_15px_rgba(6,182,212,0.15)] transition-all w-full placeholder-[var(--color-text-muted)]"
              />
              <AnimatePresence>
                {searchOpen && searchResults && (
                  <motion.div
                    initial={{ opacity: 0, y: -4, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -4, scale: 0.96 }}
                    transition={{ duration: 0.12 }}
                    className="absolute top-full mt-2 left-0 right-0 bg-[#0B1220] border border-gray-800 rounded-xl shadow-2xl shadow-black/50 overflow-hidden z-50"
                  >
                    {searching && (
                      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-800/50">
                        <div className="w-3 h-3 border-2 border-[var(--color-accent-cyan)] border-t-transparent rounded-full animate-spin" />
                        <span className="text-xs text-gray-400">Searching...</span>
                      </div>
                    )}
                    {searchResults.patients.length > 0 && (
                      <div>
                        <div className="px-4 py-1.5 text-[10px] font-mono text-gray-500 uppercase tracking-wider bg-gray-900/30">Patients</div>
                        {searchResults.patients.slice(0, 5).map(p => (
                          <button key={p.id} onClick={() => { setSearchOpen(false); setSearchQuery(''); navigate(`/dashboard/patients/${p.id}`); }}
                            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-300 hover:text-white hover:bg-[rgba(255,255,255,0.04)] transition-all text-left">
                            <User className="w-4 h-4 text-[var(--color-accent-cyan)] flex-shrink-0" />
                            <span className="flex-1 truncate">{p.name}</span>
                            <span className="text-[10px] text-gray-500 font-mono truncate max-w-[100px]">{p.state}</span>
                          </button>
                        ))}
                      </div>
                    )}
                    {searchResults.hospitals.length > 0 && (
                      <div>
                        <div className="px-4 py-1.5 text-[10px] font-mono text-gray-500 uppercase tracking-wider bg-gray-900/30">Hospitals</div>
                        {searchResults.hospitals.slice(0, 5).map(h => (
                          <button key={h.id} onClick={() => { setSearchOpen(false); setSearchQuery(''); navigate(`/dashboard/hospitals`); }}
                            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-300 hover:text-white hover:bg-[rgba(255,255,255,0.04)] transition-all text-left">
                            <Hospital className="w-4 h-4 text-[var(--color-accent-violet)] flex-shrink-0" />
                            <span className="flex-1 truncate">{h.name}</span>
                            <span className="text-[10px] text-gray-500 font-mono truncate max-w-[100px]">{h.state}</span>
                          </button>
                        ))}
                      </div>
                    )}
                    {!searching && searchResults.patients.length === 0 && searchResults.hospitals.length === 0 && (
                      <div className="px-4 py-3 text-xs text-gray-500 text-center">No results found</div>
                    )}
                    <button onClick={() => { setSearchOpen(false); navigate(`/dashboard/patients?search=${encodeURIComponent(searchQuery.trim())}`); }}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-xs text-[var(--color-accent-cyan)] border-t border-gray-800/50 hover:bg-[rgba(255,255,255,0.04)] transition-all">
                      <ExternalLink className="w-3 h-3" />
                      View all matching patients
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <button className="p-2 rounded-full text-[var(--color-text-secondary)] hover:text-white hover:bg-[var(--color-bg-elevated)] relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[var(--color-accent-rose)] border-2 border-[var(--color-bg-primary)]"></span>
            </button>

            {/* Settings dropdown */}
            <div ref={settingsRef} className="relative">
              <button
                onClick={() => setSettingsOpen(!settingsOpen)}
                className="p-2 rounded-full text-[var(--color-text-secondary)] hover:text-white hover:bg-[var(--color-bg-elevated)] transition-all"
              >
                <Settings className="w-5 h-5" />
              </button>
              <AnimatePresence>
                {settingsOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -8, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -8, scale: 0.95 }}
                    transition={{ duration: 0.15 }}
                    className="absolute right-0 top-full mt-2 w-64 bg-[#0B1220] border border-gray-800 rounded-xl shadow-2xl shadow-black/50 overflow-hidden"
                  >
                    <div className="px-4 py-3 border-b border-gray-800">
                      <p className="text-sm font-medium text-white truncate">{userInfo?.name || 'User'}</p>
                      <p className="text-xs text-gray-400 truncate">{userInfo?.role || ''}</p>
                    </div>
                    {!showSetPw ? (
                      <>
                        <button
                          onClick={() => setShowSetPw(true)}
                          className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-300 hover:text-white hover:bg-[rgba(255,255,255,0.05)] transition-all"
                        >
                          <Lock className="w-4 h-4" />
                          Set Password
                        </button>
                        <button
                          onClick={handleLogout}
                          className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-300 hover:text-white hover:bg-[rgba(255,255,255,0.05)] transition-all"
                        >
                          <LogOut className="w-4 h-4" />
                          Logout
                        </button>
                      </>
                    ) : (
                      <div className="p-4">
                        <p className="text-xs text-gray-400 mb-3">Enter a password for email login:</p>
                        <input
                          type="password"
                          value={newPw}
                          onChange={e => setNewPw(e.target.value)}
                          placeholder="New password"
                          minLength={6}
                          className="w-full bg-gray-900/50 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500/50 mb-2"
                        />
                        {pwMsg && (
                          <p className={`text-xs mb-2 ${pwMsg.includes('success') ? 'text-green-400' : 'text-red-400'}`}>{pwMsg}</p>
                        )}
                        <div className="flex gap-2">
                          <button
                            onClick={async () => {
                              setPwMsg('');
                              if (newPw.length < 6) { setPwMsg('Min 6 characters'); return; }
                              try {
                                await setPassword(newPw);
                                setPwMsg('Password set successfully');
                                setNewPw('');
                                setTimeout(() => { setShowSetPw(false); setPwMsg(''); }, 1500);
                              } catch { setPwMsg('Failed to set password'); }
                            }}
                            className="flex-1 py-2 rounded-lg bg-cyan-600 text-white text-xs font-medium hover:bg-cyan-500 transition-all"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => { setShowSetPw(false); setNewPw(''); setPwMsg(''); }}
                            className="flex-1 py-2 rounded-lg border border-gray-700 text-gray-300 text-xs font-medium hover:bg-gray-800 transition-all"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto bg-[var(--color-bg-primary)] p-4 sm:p-6 lg:p-8">
          <PageTransition>
            <Outlet />
          </PageTransition>
        </main>
      </div>
    </div>
  );
}


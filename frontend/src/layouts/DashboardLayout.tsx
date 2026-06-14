// @ts-nocheck
import React, { useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
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
  User
} from 'lucide-react';
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
  const location = useLocation();

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
        
        <div className="p-4 border-t border-[var(--color-border)]">
          <div className="flex items-center p-2 rounded-lg bg-[var(--color-bg-elevated)]">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[var(--color-accent-violet)] to-[var(--color-accent-cyan)] flex items-center justify-center text-sm font-bold text-white">
              JD
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-white">Dr. John Doe</p>
              <p className="text-xs text-[var(--color-text-muted)]">Chief Medical Officer</p>
            </div>
          </div>
        </div>
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
            <div className="relative hidden md:block w-72 group">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] group-focus-within:text-[var(--color-accent-cyan)] transition-colors" />
              <input 
                type="text" 
                placeholder="Search resources, records..." 
                className="bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.08)] text-[var(--color-text-primary)] text-sm rounded-full pl-10 pr-4 py-2 focus:outline-none focus:border-[var(--color-accent-cyan)] focus:bg-[rgba(255,255,255,0.05)] focus:shadow-[0_0_15px_rgba(6,182,212,0.15)] transition-all w-full placeholder-[var(--color-text-muted)]"
              />
            </div>
            
            <button className="p-2 rounded-full text-[var(--color-text-secondary)] hover:text-white hover:bg-[var(--color-bg-elevated)] relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[var(--color-accent-rose)] border-2 border-[var(--color-bg-primary)]"></span>
            </button>
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


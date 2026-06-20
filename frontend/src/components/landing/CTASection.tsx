import React, { useEffect, useState } from 'react';
import { motion, useInView } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { GradientText } from './ui/GradientText';

const TerminalLogs = ({ isVisible }: { isVisible: boolean }) => {
  const [logs, setLogs] = useState<string[]>([]);
  
  const allLogs = [
    "> Initializing XGBoost predictors... OK",
    "> Connecting to national health grid... ESTABLISHED",
    "> Fetching real-time bed capacity matrices... LOADED",
    "> Compiling 6-model ensemble... READY",
    "> Waiting for intelligence query..."
  ];

  useEffect(() => {
    if (!isVisible) return;
    let currentLog = 0;
    const interval = setInterval(() => {
      if (currentLog < allLogs.length) {
        setLogs(prev => [...prev, allLogs[currentLog]]);
        currentLog++;
      } else {
        clearInterval(interval);
      }
    }, 400);
    return () => clearInterval(interval);
  }, [isVisible]);

  return (
    <div className="w-full max-w-2xl mx-auto bg-black/60 rounded-xl border border-[var(--color-border-subtle)] p-6 font-mono text-sm shadow-2xl backdrop-blur-md text-left mt-16 min-h-[180px]">
      <div className="flex gap-2 mb-4">
        <div className="w-3 h-3 rounded-full bg-[var(--color-accent-rose)] opacity-50" />
        <div className="w-3 h-3 rounded-full bg-[var(--color-accent-amber)] opacity-50" />
        <div className="w-3 h-3 rounded-full bg-[var(--color-accent-emerald)] opacity-50" />
      </div>
      {logs.map((log, i) => (
        <motion.div 
          key={i} 
          initial={{ opacity: 0, x: -10 }} 
          animate={{ opacity: 1, x: 0 }}
          className="text-[var(--color-accent-emerald)] mb-2"
        >
          {log}
        </motion.div>
      ))}
      {logs.length === allLogs.length && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 1, 0] }}
          transition={{ repeat: Infinity, duration: 1 }}
          className="w-2 h-4 bg-[var(--color-accent-cyan)] mt-2"
        />
      )}
    </div>
  );
};

const CTASection = () => {
  const navigate = useNavigate();
  const ref = React.useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section 
      ref={ref}
      className="py-32 relative w-full flex flex-col items-center justify-center transition-colors duration-[2000ms] ease-in-out"
      style={{ backgroundColor: isInView ? 'var(--landing-bg-void)' : 'transparent' }}
    >
      {/* Cinematic background glow that fades out */}
      <motion.div 
        animate={{ opacity: isInView ? 0 : 0.2 }}
        transition={{ duration: 2 }}
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-to-br from-[var(--color-accent-cyan)] to-[var(--color-accent-violet)] rounded-full blur-[120px] pointer-events-none" 
      />
      
      <div className="relative z-10 max-w-4xl mx-auto text-center px-6">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.8 }}
        >
          <GradientText as="h2" className="text-5xl md:text-7xl font-bold mb-8 tracking-tight leading-tight">
            Ready to transform <br/> healthcare delivery?
          </GradientText>
        </motion.div>
        
        <motion.p 
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="text-xl text-[var(--color-text-secondary)] mb-12 max-w-2xl mx-auto"
        >
          Join hundreds of leading institutions using HospitalIQ to predict demand, allocate resources, and improve patient outcomes.
        </motion.p>
        
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={isInView ? { opacity: 1, scale: 1 } : {}}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          <button 
            onClick={() => navigate('/login')}
            className="group relative px-12 py-5 rounded-full bg-white text-[#05080f] font-bold text-xl overflow-hidden shadow-[0_0_40px_rgba(255,255,255,0.1)] transition-transform hover:scale-105 duration-300"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-[var(--color-accent-cyan)] to-[var(--color-accent-violet)] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <span className="relative z-10 flex items-center gap-3 group-hover:text-white transition-colors">
              Launch Intelligence
              <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </span>
          </button>
        </motion.div>

        {/* Terminal Logs */}
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.8, delay: 0.8 }}
        >
          <TerminalLogs isVisible={isInView} />
        </motion.div>
      </div>
    </section>
  );
};

export default CTASection;

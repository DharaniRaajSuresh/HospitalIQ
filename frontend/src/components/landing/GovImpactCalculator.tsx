import React, { useState, useEffect } from 'react';
import { motion, useAnimation, useInView } from 'framer-motion';
import { TrendingUp, Users, HeartPulse, Building2 } from 'lucide-react';

function Counter({ value, prefix = "", suffix = "" }: { value: number; prefix?: string; suffix?: string }) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const duration = 1000; // ms
    const steps = 60;
    const stepTime = Math.abs(Math.floor(duration / steps));
    let current = display;
    const diff = value - current;
    const increment = diff / steps;

    const timer = setInterval(() => {
      current += increment;
      if ((increment > 0 && current >= value) || (increment < 0 && current <= value)) {
        current = value;
        clearInterval(timer);
      }
      setDisplay(current);
    }, stepTime);

    return () => clearInterval(timer);
  }, [value]);

  // Format number intelligently
  let formatted = Math.round(display).toLocaleString();
  if (value >= 1000000) {
    formatted = (display / 1000000).toFixed(1) + 'M';
  } else if (value >= 1000) {
    formatted = (display / 1000).toFixed(1) + 'k';
  }

  return <span className="font-mono">{prefix}{formatted}{suffix}</span>;
}

export default function GovImpactCalculator() {
  const [populationStr, setPopulationStr] = useState("50"); // in millions
  const population = Number(populationStr);
  
  // Fake ROI calculations based on population scale
  const bedsOptimized = Math.round(population * 1250);
  const livesSaved = Math.round(population * 84.5);
  const costSaved = Math.round(population * 2.4); // In millions
  const hospitalsConnected = Math.round(population * 18);

  const ref = React.useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });
  const controls = useAnimation();

  useEffect(() => {
    if (isInView) {
      controls.start("visible");
    }
  }, [isInView, controls]);

  return (
    <section ref={ref} className="w-full max-w-5xl mx-auto px-6 py-24">
      <motion.div 
        variants={{
          hidden: { opacity: 0, y: 50 },
          visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: "easeOut" } }
        }}
        initial="hidden"
        animate={controls}
        className="bg-[#0B1220] border border-[rgba(255,255,255,0.05)] rounded-[3rem] p-8 md:p-16 shadow-2xl relative overflow-hidden"
      >
        {/* Decorative Grid */}
        <div className="absolute inset-0 opacity-20 pointer-events-none"
             style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, rgba(255,255,255,0.15) 1px, transparent 0)', backgroundSize: '32px 32px' }} />
        
        <div className="relative z-10 text-center mb-12">
          <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-white mb-4">Projected National Impact</h2>
          <p className="text-[var(--color-text-muted)] text-lg max-w-2xl mx-auto">
            Drag the slider to estimate the actionable impact HospitalIQ can deliver based on your state or national population size.
          </p>
        </div>

        {/* Interactive Slider */}
        <div className="relative z-10 max-w-3xl mx-auto mb-16 bg-[#020617] p-6 rounded-2xl border border-[rgba(255,255,255,0.05)]">
          <div className="flex justify-between text-sm font-mono text-[var(--color-text-muted)] mb-4">
            <span>10M Citizens</span>
            <span className="text-amber-400 font-bold text-lg">{population} Million Citizens</span>
            <span>1.4B Citizens</span>
          </div>
          <input 
            type="range" 
            min="10" 
            max="1400" 
            step="10"
            value={population} 
            onChange={(e) => setPopulationStr(e.target.value)}
            className="w-full h-2 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-amber-500 hover:accent-amber-400 transition-all"
          />
        </div>

        {/* Impact Metrics Grid */}
        <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-[#020617] border border-[rgba(255,255,255,0.05)] rounded-2xl p-6 text-center group hover:border-amber-500/30 transition-colors">
            <div className="w-12 h-12 rounded-full bg-blue-500/10 text-blue-400 mx-auto flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <Building2 className="w-6 h-6" />
            </div>
            <div className="text-3xl font-bold text-white mb-1">
              <Counter value={bedsOptimized} />
            </div>
            <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider font-mono">Beds Optimized</div>
          </div>

          <div className="bg-[#020617] border border-[rgba(255,255,255,0.05)] rounded-2xl p-6 text-center group hover:border-rose-500/30 transition-colors">
            <div className="w-12 h-12 rounded-full bg-rose-500/10 text-rose-400 mx-auto flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <HeartPulse className="w-6 h-6" />
            </div>
            <div className="text-3xl font-bold text-white mb-1">
              <Counter value={livesSaved} />
            </div>
            <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider font-mono">Est. Lives Saved</div>
          </div>

          <div className="bg-[#020617] border border-[rgba(255,255,255,0.05)] rounded-2xl p-6 text-center group hover:border-emerald-500/30 transition-colors">
            <div className="w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-400 mx-auto flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <TrendingUp className="w-6 h-6" />
            </div>
            <div className="text-3xl font-bold text-white mb-1">
              <Counter value={costSaved} prefix="$" suffix="M" />
            </div>
            <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider font-mono">Logistics Saved</div>
          </div>

          <div className="bg-[#020617] border border-[rgba(255,255,255,0.05)] rounded-2xl p-6 text-center group hover:border-cyan-500/30 transition-colors">
            <div className="w-12 h-12 rounded-full bg-cyan-500/10 text-cyan-400 mx-auto flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <Users className="w-6 h-6" />
            </div>
            <div className="text-3xl font-bold text-white mb-1">
              <Counter value={hospitalsConnected} />
            </div>
            <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider font-mono">Hospitals Synced</div>
          </div>
        </div>
      </motion.div>
    </section>
  );
}

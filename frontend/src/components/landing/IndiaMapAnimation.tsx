import React from 'react';
import { motion } from 'framer-motion';
import { GradientText } from './ui/GradientText';

const HolographicTooltip = ({ state, value, x, y, delay }: { state: string, value: string, x: string, y: string, delay: number }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.8, y: 10 }}
    whileInView={{ opacity: 1, scale: 1, y: 0 }}
    viewport={{ once: true }}
    transition={{ delay, duration: 0.5 }}
    className="absolute z-20 pointer-events-none"
    style={{ left: x, top: y }}
  >
    <div className="relative">
      {/* Connector line */}
      <div className="absolute top-full left-4 w-px h-8 bg-gradient-to-b from-[var(--color-accent-cyan)] to-transparent" />
      {/* Tooltip box */}
      <div className="bg-[rgba(11,18,32,0.8)] backdrop-blur-md border border-[var(--color-accent-cyan)] p-2 rounded-lg shadow-[0_0_15px_rgba(0,240,255,0.2)]">
        <p className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">{state}</p>
        <p className="text-sm font-mono text-[var(--color-accent-cyan)]">{value}</p>
      </div>
    </div>
  </motion.div>
);

const IndiaMapAnimation = () => {
  return (
    <div className="flex flex-col lg:flex-row items-center justify-between w-full h-[600px] relative p-12">
      <div className="flex-1 lg:pr-12 z-10">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[var(--color-surface-2)] border border-[var(--color-border-subtle)] mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent-rose)] animate-pulse" />
          <span className="text-[10px] font-semibold text-[var(--color-text-secondary)] tracking-widest uppercase">
            Live Monitoring
          </span>
        </div>
        
        <GradientText as="h2" className="text-4xl md:text-5xl font-bold mb-6 leading-tight">
          National Risk Map
        </GradientText>
        <p className="text-xl text-[var(--color-text-secondary)] mb-8 font-light max-w-md">
          Visualize healthcare demand and resource allocation across India in real-time. Identify critical hotspots before they reach capacity.
        </p>
        <ul className="space-y-4">
          {[
            { text: "Real-time ICU bed availability", color: "bg-[var(--color-accent-cyan)]", shadow: "shadow-glow-cyan" },
            { text: "Epidemiological trend tracking", color: "bg-[var(--color-accent-violet)]", shadow: "shadow-glow-violet" },
            { text: "Resource reallocation algorithms", color: "bg-[var(--color-accent-emerald)]", shadow: "shadow-glow-emerald" }
          ].map((item, idx) => (
            <motion.li 
              key={idx}
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1 + 0.3 }}
              className="flex items-center text-[var(--color-text-primary)] font-medium"
            >
              <div className={`w-2 h-2 rounded-full ${item.color} mr-4 ${item.shadow}`} />
              {item.text}
            </motion.li>
          ))}
        </ul>
      </div>

      <div className="flex-1 h-full relative w-full perspective-[1200px]">
        {/* Isometric Map Container */}
        <motion.div
          initial={{ rotateX: 60, rotateZ: -45, y: 100, opacity: 0 }}
          whileInView={{ rotateX: 60, rotateZ: -45, y: 0, opacity: 1 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1] }}
          className="absolute inset-0 transform-style-3d flex items-center justify-center pointer-events-none"
        >
          {/* Base glowing grid representing India bounds */}
          <div className="w-[400px] h-[500px] border border-[var(--color-border-strong)] bg-[var(--color-surface-1)] shadow-[0_0_50px_rgba(0,240,255,0.1)] relative">
            {/* Grid pattern */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:40px_40px]" />
            
            {/* Map nodes */}
            {[
              { top: '30%', left: '35%', color: 'var(--color-accent-rose)' }, // Delhi
              { top: '55%', left: '25%', color: 'var(--color-accent-emerald)' }, // Mumbai
              { top: '75%', left: '40%', color: 'var(--color-accent-cyan)' }, // Bangalore
              { top: '45%', left: '60%', color: 'var(--color-accent-violet)' }, // Kolkata
            ].map((node, i) => (
              <div
                key={i}
                className="absolute w-4 h-4 rounded-full -ml-2 -mt-2 shadow-2xl"
                style={{ top: node.top, left: node.left, backgroundColor: node.color, boxShadow: `0 0 20px ${node.color}` }}
              >
                <div className="absolute inset-0 rounded-full border border-current animate-ping opacity-75" />
              </div>
            ))}

            {/* Arcing connection lines (simulated with SVG) */}
            <svg className="absolute inset-0 w-full h-full" style={{ overflow: 'visible' }}>
              <path d="M 140 150 Q 200 50 240 225" fill="none" stroke="rgba(0,240,255,0.4)" strokeWidth="2" strokeDasharray="5,5" className="animate-[dash_20s_linear_infinite]" />
              <path d="M 100 275 Q 150 200 160 375" fill="none" stroke="rgba(0,255,157,0.4)" strokeWidth="2" strokeDasharray="5,5" className="animate-[dash_20s_linear_infinite]" />
            </svg>
          </div>
        </motion.div>

        {/* 2D Overlay Tooltips (Not rotated) */}
        <div className="absolute inset-0 pointer-events-none">
          <HolographicTooltip state="Maharashtra" value="ICU: 92% CAP" x="20%" y="45%" delay={1} />
          <HolographicTooltip state="Delhi" value="RISK: CRITICAL" x="35%" y="20%" delay={1.2} />
          <HolographicTooltip state="Karnataka" value="BEDS: OK" x="50%" y="70%" delay={1.4} />
        </div>

      </div>
      <style>{`
        @keyframes dash {
          to { stroke-dashoffset: -1000; }
        }
      `}</style>
    </div>
  );
};

export default IndiaMapAnimation;

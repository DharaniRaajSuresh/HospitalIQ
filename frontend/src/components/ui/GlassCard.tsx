import React, { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

const GlassCard = ({ children, className, hover = true, ...props }: any) => {
  const divRef = useRef<HTMLDivElement>(null);
  const [isFocused, setIsFocused] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [opacity, setOpacity] = useState(0);

  const handleMouseMove = (e) => {
    if (!divRef.current || isFocused) return;
    const div = divRef.current;
    const rect = div.getBoundingClientRect();
    setPosition({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  const handleFocus = () => {
    setIsFocused(true);
    setOpacity(1);
  };

  const handleBlur = () => {
    setIsFocused(false);
    setOpacity(0);
  };

  const handleMouseEnter = () => setOpacity(1);
  const handleMouseLeave = () => setOpacity(0);

  return (
    <motion.div
      ref={divRef}
      onMouseMove={handleMouseMove}
      onFocus={handleFocus}
      onBlur={handleBlur}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className={cn(
        'relative isolate rounded-2xl p-6 text-[var(--color-text-primary)] overflow-hidden bg-[rgba(15,23,42,0.6)] backdrop-blur-2xl border border-white/5 shadow-[0_8px_32px_rgba(0,0,0,0.5)]',
        hover && 'transition-transform duration-500 hover:-translate-y-1',
        className
      )}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      {...props}
    >
      {/* Dynamic Background Spotlight */}
      <div
        className="pointer-events-none absolute -inset-px transition-opacity duration-500 z-[-1]"
        style={{
          opacity,
          background: `radial-gradient(800px circle at ${position.x}px ${position.y}px, rgba(0,240,255,0.06), transparent 40%)`,
        }}
      />
      
      {/* Dynamic Border Spotlight */}
      <div
        className="pointer-events-none absolute -inset-px rounded-2xl opacity-0 transition-opacity duration-500 z-[-1]"
        style={{
          opacity,
          background: `radial-gradient(500px circle at ${position.x}px ${position.y}px, rgba(0, 240, 255, 0.4), transparent 40%) border-box`,
          WebkitMask: `linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0)`,
          WebkitMaskComposite: 'xor',
          maskComposite: 'exclude',
          border: '1px solid transparent',
        }}
      />

      {/* VisionOS Noise Texture */}
      <div 
        className="pointer-events-none absolute inset-0 opacity-[0.02] mix-blend-overlay z-[-1]"
        style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }}
      />

      {children}
    </motion.div>
  );
};

export default GlassCard;

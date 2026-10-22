import React, { ReactNode } from 'react';
import { motion } from 'framer-motion';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  delay?: number;
}

export const GlassCard: React.FC<GlassCardProps> = ({ children, className = '', delay = 0 }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.8, delay, ease: [0.16, 1, 0.3, 1] }}
      className={`relative group overflow-hidden rounded-[2rem] bg-[#0B1220]/40 backdrop-blur-[20px] border border-[rgba(255,255,255,0.08)] shadow-2xl ${className}`}
    >
      {/* Subtle hover shine effect */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-700 bg-gradient-to-br from-[rgba(255,255,255,0.05)] to-transparent pointer-events-none" />
      {children}
    </motion.div>
  );
};

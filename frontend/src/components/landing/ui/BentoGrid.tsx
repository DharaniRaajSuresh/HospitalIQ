import React, { ReactNode } from 'react';

interface BentoGridProps {
  children: ReactNode;
  className?: string;
}

export const BentoGrid: React.FC<BentoGridProps> = ({ children, className = '' }) => {
  return (
    <div className={`grid grid-cols-1 md:grid-cols-3 gap-4 max-w-7xl mx-auto ${className}`}>
      {children}
    </div>
  );
};

interface BentoGridItemProps {
  children: ReactNode;
  className?: string;
}

export const BentoGridItem: React.FC<BentoGridItemProps> = ({ children, className = '' }) => {
  return (
    <div
      className={`row-span-1 rounded-[2rem] bg-[#0B1220]/40 backdrop-blur-[20px] border border-[rgba(255,255,255,0.08)] shadow-2xl p-6 flex flex-col space-y-4 overflow-hidden relative group ${className}`}
    >
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-700 bg-gradient-to-br from-[rgba(255,255,255,0.05)] to-transparent pointer-events-none" />
      {children}
    </div>
  );
};

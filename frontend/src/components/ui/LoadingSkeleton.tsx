import React from 'react';
import { cn } from '../../lib/utils';

const LoadingSkeleton = ({ variant = 'card', className }) => {
  const baseClass = "skeleton bg-elevated/50 relative overflow-hidden";
  const shimmerClass = "before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_2s_infinite] before:bg-gradient-to-r before:from-transparent before:via-white/5 before:to-transparent";

  if (variant === 'card') {
    return (
      <div className={cn("glass border border-[rgba(255,255,255,0.06)] bg-glass p-6 rounded-xl flex flex-col gap-4", className)}>
        <div className="flex justify-between items-center">
          <div className={cn(baseClass, shimmerClass, "w-24 h-4 rounded-md")} />
          <div className={cn(baseClass, shimmerClass, "w-8 h-8 rounded-full")} />
        </div>
        <div className="mt-4">
          <div className={cn(baseClass, shimmerClass, "w-32 h-8 rounded-md")} />
        </div>
      </div>
    );
  }

  if (variant === 'chart') {
    return (
      <div className={cn("glass border border-[rgba(255,255,255,0.06)] bg-glass p-6 rounded-xl flex flex-col gap-6 h-[300px]", className)}>
        <div className={cn(baseClass, shimmerClass, "w-48 h-6 rounded-md")} />
        <div className="flex-1 flex items-end gap-2">
          {[40, 70, 45, 90, 65, 30, 85].map((h, i) => (
            <div key={i} className={cn(baseClass, shimmerClass, "flex-1 rounded-t-sm rounded-b-none")} style={{ height: `${h}%` }} />
          ))}
        </div>
      </div>
    );
  }

  if (variant === 'table') {
    return (
      <div className={cn("glass border border-[rgba(255,255,255,0.06)] bg-glass rounded-xl overflow-hidden", className)}>
        <div className="p-4 border-b border-[rgba(255,255,255,0.06)] flex gap-4">
          <div className={cn(baseClass, shimmerClass, "w-1/4 h-4 rounded-md")} />
          <div className={cn(baseClass, shimmerClass, "w-1/4 h-4 rounded-md")} />
          <div className={cn(baseClass, shimmerClass, "w-1/4 h-4 rounded-md")} />
          <div className={cn(baseClass, shimmerClass, "w-1/4 h-4 rounded-md")} />
        </div>
        {[1, 2, 3, 4, 5].map((row) => (
          <div key={row} className="p-4 border-b border-[rgba(255,255,255,0.02)] flex gap-4">
            <div className={cn(baseClass, shimmerClass, "w-1/4 h-4 rounded-md opacity-70")} />
            <div className={cn(baseClass, shimmerClass, "w-1/4 h-4 rounded-md opacity-70")} />
            <div className={cn(baseClass, shimmerClass, "w-1/4 h-4 rounded-md opacity-70")} />
            <div className={cn(baseClass, shimmerClass, "w-1/4 h-4 rounded-md opacity-70")} />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={cn(baseClass, shimmerClass, "rounded-lg", className)} />
  );
};

export default LoadingSkeleton;

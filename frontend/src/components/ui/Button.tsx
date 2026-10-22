import React from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

import { cn } from '../../lib/utils';

interface ButtonProps extends React.ComponentPropsWithoutRef<typeof motion.button> {
  children?: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  className?: string;
  isLoading?: boolean;
  icon?: React.ComponentType<{ className?: string }>;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ 
  children, 
  variant = 'primary', 
  size = 'md', 
  className, 
  isLoading = false,
  icon: Icon,
  disabled,
  ...props 
}, ref) => {
  const variants: Record<string, string> = {
    primary: "bg-gradient-to-r from-[var(--color-accent-cyan)] to-[var(--color-accent-violet)] text-white shadow-[0_4px_14px_rgba(6,182,212,0.39)] hover:shadow-[0_6px_20px_rgba(6,182,212,0.6)] border-transparent border-t-[rgba(255,255,255,0.2)]",
    secondary: "bg-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.08)] text-[var(--color-text-primary)] border border-[rgba(255,255,255,0.08)] hover:border-[rgba(255,255,255,0.2)] shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]",
    ghost: "bg-transparent hover:bg-[rgba(255,255,255,0.04)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border-transparent",
    danger: "bg-[rgba(244,63,94,0.1)] hover:bg-[rgba(244,63,94,0.2)] text-rose-400 border border-[rgba(244,63,94,0.2)] hover:border-[rgba(244,63,94,0.4)]",
  };

  const sizes: Record<string, string> = {
    sm: "px-3 py-1.5 text-xs",
    md: "px-4 py-2 text-sm",
    lg: "px-6 py-3 text-base",
    icon: "p-2",
  };

  return (
    <motion.button
      ref={ref}
      whileHover={{ scale: disabled || isLoading ? 1 : 1.02 }}
      whileTap={{ scale: disabled || isLoading ? 1 : 0.98 }}
      disabled={disabled || isLoading}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors border backdrop-blur-sm outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50 disabled:opacity-50 disabled:cursor-not-allowed",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
      {!isLoading && Icon && <Icon className={cn(size === 'sm' ? 'w-3 h-3' : 'w-4 h-4')} />}
      {children}
    </motion.button>
  );
});

Button.displayName = 'Button';

export default Button;

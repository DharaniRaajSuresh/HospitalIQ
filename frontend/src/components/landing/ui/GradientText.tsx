import React from 'react';

interface GradientTextProps {
  as?: 'h1' | 'h2' | 'h3' | 'span' | 'p';
  children: React.ReactNode;
  className?: string;
  animate?: boolean;
}

export const GradientText: React.FC<GradientTextProps> = ({ 
  as: Component = 'span', 
  children, 
  className = '',
  animate = true 
}) => {
  const baseStyle = "text-transparent bg-clip-text bg-gradient-to-r from-[#00ff9d] via-[#00f0ff] to-[#b026ff]";
  const animateStyle = animate ? "animate-gradient-x bg-[length:200%_auto]" : "";
  
  return (
    <Component className={`${baseStyle} ${animateStyle} ${className}`}>
      {children}
    </Component>
  );
};

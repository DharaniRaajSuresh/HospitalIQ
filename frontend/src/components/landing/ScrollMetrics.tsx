import React, { useEffect, useState } from 'react';
import { useScrollReveal } from '../../hooks/useScrollReveal';
import { GradientText } from './ui/GradientText';
import { GlassCard } from './ui/GlassCard';

interface AnimatedCounterProps {
  end: number;
  duration?: number;
  suffix?: string;
  prefix?: string;
  isVisible: boolean;
}

const AnimatedCounter: React.FC<AnimatedCounterProps> = ({ end, duration = 2, suffix = '', prefix = '', isVisible }) => {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (isVisible) {
      let startTime: number | null = null;
      let animationFrame: number;
      
      const animate = (timestamp: number) => {
        if (!startTime) startTime = timestamp;
        const progress = Math.min((timestamp - startTime) / (duration * 1000), 1);
        
        // Easing out cubic
        const easeOut = 1 - Math.pow(1 - progress, 3);
        setCount(Math.floor(easeOut * end));
        
        if (progress < 1) {
          animationFrame = requestAnimationFrame(animate);
        } else {
          setCount(end);
        }
      };
      
      animationFrame = requestAnimationFrame(animate);
      return () => cancelAnimationFrame(animationFrame);
    }
  }, [end, duration, isVisible]);

  return <span className="font-mono">{prefix}{count.toLocaleString()}{suffix}</span>;
};

const MarqueeText = () => (
  <div className="absolute top-1/2 -translate-y-1/2 left-0 w-[200%] flex overflow-hidden whitespace-nowrap opacity-[0.03] pointer-events-none select-none z-0">
    <div className="animate-[marquee_60s_linear_infinite] flex items-center">
      <span className="text-[12rem] font-bold px-10">REAL-TIME FORECASTING</span>
      <span className="text-[12rem] font-bold px-10">PREDICTIVE MORTALITY</span>
      <span className="text-[12rem] font-bold px-10">ENSEMBLE MODELS</span>
      <span className="text-[12rem] font-bold px-10">REAL-TIME FORECASTING</span>
      <span className="text-[12rem] font-bold px-10">PREDICTIVE MORTALITY</span>
      <span className="text-[12rem] font-bold px-10">ENSEMBLE MODELS</span>
    </div>
  </div>
);

const ScrollMetrics = () => {
  const { ref, isVisible } = useScrollReveal({ threshold: 0.5 });

  const metrics = [
    { label: "Patient Records", value: 50000000, suffix: "+", color: "from-[var(--color-accent-cyan)]" },
    { label: "Hospitals Tracked", value: 8400, suffix: "+", color: "from-[var(--color-accent-emerald)]" },
    { label: "Prediction Accuracy", value: 98, suffix: "%", color: "from-[var(--color-accent-violet)]" }
  ];

  return (
    <div className="w-full relative py-32 flex flex-col items-center overflow-hidden">
      <MarqueeText />
      
      <div className="text-center mb-20 relative z-10">
        <GradientText as="h2" className="text-5xl md:text-7xl font-extrabold mb-6 tracking-tighter">
          Unprecedented Scale
        </GradientText>
        <p className="text-xl md:text-2xl text-[var(--color-text-secondary)] max-w-3xl mx-auto font-light leading-relaxed">
          Harnessing massive national datasets to provide real-time operational insights across the healthcare continuum.
        </p>
      </div>

      <div ref={ref as any} className="grid grid-cols-1 md:grid-cols-3 gap-8 w-full max-w-6xl px-6 relative z-10">
        {metrics.map((metric, idx) => (
          <GlassCard key={idx} delay={idx * 0.2} className="p-10 !rounded-[2.5rem] group">
            <div className={`absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r ${metric.color} to-transparent opacity-50 group-hover:opacity-100 transition-opacity duration-500`} />
            <h3 className="text-6xl md:text-[80px] font-bold text-white mb-6 tracking-tighter">
              <AnimatedCounter end={metric.value} suffix={metric.suffix} isVisible={isVisible} />
            </h3>
            <div className="flex items-center gap-3">
              <div className={`w-2 h-2 rounded-full bg-gradient-to-r ${metric.color} to-white shadow-[0_0_10px_rgba(255,255,255,0.5)]`} />
              <p className="text-[var(--color-text-secondary)] text-sm md:text-base font-medium uppercase tracking-[0.2em]">{metric.label}</p>
            </div>
          </GlassCard>
        ))}
      </div>

      <style>{`
        @keyframes marquee {
          0% { transform: translateX(0%); }
          100% { transform: translateX(-50%); }
        }
      `}</style>
    </div>
  );
};

export default ScrollMetrics;

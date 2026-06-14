import React, { useEffect, useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';

const AnimatedCounter = ({ end, duration = 2, suffix = '', prefix = '' }) => {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true });

  useEffect(() => {
    if (isInView) {
      let startTime;
      let animationFrame;
      
      const animate = (timestamp) => {
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
  }, [end, duration, isInView]);

  return <span ref={ref}>{prefix}{count.toLocaleString()}{suffix}</span>;
};

const ScrollMetrics = () => {
  return (
    <div className="w-full flex flex-col items-center">
      <div className="text-center mb-16">
        <h2 className="text-4xl md:text-6xl font-bold text-[var(--color-text-primary)] mb-6">
          Unprecedented Scale
        </h2>
        <p className="text-xl text-[var(--color-text-secondary)] max-w-2xl mx-auto">
          Harnessing massive datasets to provide real-time operational insights across the healthcare continuum.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 w-full max-w-5xl">
        {[
          { label: "Patient Records", value: 46000, suffix: "+", color: "from-[#06b6d4]" },
          { label: "Hospitals Tracked", value: 500, suffix: "+", color: "from-[#10b981]" },
          { label: "Accuracy Rate", value: 98, suffix: "%", color: "from-[#8b5cf6]" }
        ].map((metric, idx) => (
          <motion.div 
            key={idx}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: idx * 0.2, duration: 0.8 }}
            className="p-8 rounded-3xl bg-[var(--color-bg-card)] border border-[rgba(255,255,255,0.05)] relative overflow-hidden group"
          >
            <div className={`absolute top-0 left-0 w-full h-1 bg-gradient-to-r ${metric.color} to-transparent opacity-50 group-hover:opacity-100 transition-opacity`} />
            <h3 className="text-5xl md:text-6xl font-bold text-[var(--color-text-primary)] mb-4 font-mono">
              <AnimatedCounter end={metric.value} suffix={metric.suffix} />
            </h3>
            <p className="text-[var(--color-text-secondary)] text-lg uppercase tracking-wider">{metric.label}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default ScrollMetrics;

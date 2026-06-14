import React, { useState, useEffect } from 'react';
import { motion, useInView } from 'framer-motion';

const TypewriterText = ({ text, delay = 0, start = false }) => {
  const [displayed, setDisplayed] = useState('');

  useEffect(() => {
    if (!start) return;
    
    let i = 0;
    const timer = setTimeout(() => {
      const interval = setInterval(() => {
        setDisplayed(text.substring(0, i));
        i++;
        if (i > text.length) clearInterval(interval);
      }, 30);
      return () => clearInterval(interval);
    }, delay);
    
    return () => clearTimeout(timer);
  }, [text, delay, start]);

  return <span>{displayed}{displayed.length < text.length && start && <span className="animate-pulse">|</span>}</span>;
};

const AIChatDemo = () => {
  const ref = React.useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-20%" });

  return (
    <div className="flex flex-col items-center w-full" ref={ref}>
      <div className="text-center mb-16">
        <h2 className="text-4xl md:text-5xl font-bold text-[var(--color-text-primary)] mb-6">
          Your AI Healthcare Copilot
        </h2>
        <p className="text-xl text-[var(--color-text-secondary)] max-w-2xl mx-auto">
          Query patient data, generate reports, and get actionable insights using natural language.
        </p>
      </div>

      <div className="w-full max-w-3xl bg-[#111827] rounded-3xl border border-[rgba(255,255,255,0.1)] p-6 md:p-8 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-[#8b5cf6] to-[#06b6d4]" />
        
        <div className="space-y-6">
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.5 }}
            className="flex justify-end"
          >
            <div className="bg-[#151c2c] border border-[rgba(255,255,255,0.05)] text-[var(--color-text-primary)] rounded-2xl rounded-tr-sm px-6 py-4 max-w-[80%] shadow-lg">
              Show me the bed occupancy forecast for Cardiology over the next 48 hours.
            </div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.5, delay: 1 }}
            className="flex justify-start"
          >
            <div className="bg-[rgba(6,182,212,0.1)] border border-[rgba(6,182,212,0.2)] text-[var(--color-text-primary)] rounded-2xl rounded-tl-sm px-6 py-4 max-w-[80%] shadow-lg font-mono text-sm leading-relaxed">
              <TypewriterText 
                start={isInView} 
                delay={1500} 
                text="Analyzing historical admission rates and current inpatient census... The Cardiology ward is currently at 85% capacity. Based on predictive modeling, occupancy is expected to peak at 94% tomorrow at 14:00. I recommend preparing 3 overflow beds in the general observation unit." 
              />
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default AIChatDemo;

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const NeuralNetworkViz = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [showChart, setShowChart] = useState(false);

  const steps = [
    "Ingesting 10M+ patient records...",
    "Running XGBoost mortality predictor...",
    "Running Random Forest risk classifier...",
    "Computing 95% confidence intervals...",
    "Generating 24-month trajectory..."
  ];

  useEffect(() => {
    let currentStep = 0;
    const interval = setInterval(() => {
      if (currentStep < steps.length - 1) {
        currentStep++;
        setActiveStep(currentStep);
      } else {
        clearInterval(interval);
        setTimeout(() => setShowChart(true), 500);
      }
    }, 800);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full h-full min-h-[300px] flex flex-col md:flex-row items-center justify-center gap-8 p-6">
      
      {/* Left side: ML Pipeline */}
      <div className="flex-1 w-full flex flex-col justify-center space-y-4">
        {steps.map((step, idx) => (
          <div key={idx} className="flex items-center gap-3">
            <div className="w-5 h-5 flex-shrink-0 flex items-center justify-center">
              {idx < activeStep ? (
                <div className="w-4 h-4 rounded-full bg-[var(--color-accent-emerald)] shadow-glow-emerald flex items-center justify-center">
                  <svg className="w-3 h-3 text-[var(--landing-bg-dark)]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
                </div>
              ) : idx === activeStep ? (
                <div className="w-4 h-4 rounded-full border-2 border-[var(--color-accent-cyan)] border-t-transparent animate-spin" />
              ) : (
                <div className="w-4 h-4 rounded-full border border-[var(--color-border-strong)]" />
              )}
            </div>
            <span className={`text-sm font-mono transition-colors duration-300 ${idx <= activeStep ? 'text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}`}>
              {step}
            </span>
          </div>
        ))}
      </div>

      {/* Right side: Simulated Chart */}
      <div className="flex-1 w-full h-[200px] bg-[var(--color-surface-1)] rounded-xl border border-[var(--color-border-subtle)] relative overflow-hidden flex items-end">
        {/* Grid background */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:20px_20px]" />
        
        {/* Simulated Graph Line (SVG) */}
        <AnimatePresence>
          {showChart && (
            <motion.svg 
              initial={{ opacity: 0, pathLength: 0 }}
              animate={{ opacity: 1, pathLength: 1 }}
              transition={{ duration: 1.5, ease: "easeInOut" }}
              className="absolute inset-0 w-full h-full drop-shadow-[0_0_15px_rgba(0,240,255,0.5)]" 
              preserveAspectRatio="none" 
              viewBox="0 0 100 100"
            >
              {/* Fake Confidence Interval Area */}
              <motion.path 
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.2 }}
                transition={{ delay: 1 }}
                d="M 0,80 Q 20,70 40,60 T 80,30 L 100,20 L 100,100 L 0,100 Z" 
                fill="var(--color-accent-cyan)" 
              />
              {/* Fake Prediction Line */}
              <motion.path 
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1.5, ease: "easeInOut" }}
                d="M 0,80 Q 20,70 40,60 T 80,30 L 100,20" 
                fill="none" 
                stroke="var(--color-accent-cyan)" 
                strokeWidth="2" 
                strokeLinecap="round"
              />
              
              {/* Surge Threshold Line */}
              <motion.line 
                initial={{ opacity: 0, x1: -100, x2: 0 }}
                animate={{ opacity: 0.5, x1: 0, x2: 100 }}
                transition={{ delay: 0.5 }}
                x1="0" y1="40" x2="100" y2="40" 
                stroke="var(--color-accent-rose)" 
                strokeWidth="1" 
                strokeDasharray="2,2" 
              />
            </motion.svg>
          )}
        </AnimatePresence>

        {/* Floating tooltip mock */}
        <AnimatePresence>
          {showChart && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.5 }}
              className="absolute top-4 left-4 bg-[var(--landing-bg-dark)] border border-[var(--color-border-strong)] rounded-md p-2 shadow-xl"
            >
              <div className="text-[8px] text-[var(--color-text-muted)] uppercase mb-1">Peak Prediction</div>
              <div className="text-xs font-mono text-[var(--color-accent-cyan)] font-bold">1,240 Beds Needed</div>
              <div className="text-[8px] text-[var(--color-accent-rose)] mt-1">Crosses Surge Capacity</div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

    </div>
  );
};

export default NeuralNetworkViz;

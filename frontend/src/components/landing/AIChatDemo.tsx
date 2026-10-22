import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

const TypewriterText = ({ text, delay = 0, start = false, onComplete }: { text: string, delay?: number, start?: boolean, onComplete?: () => void }) => {
  const [displayed, setDisplayed] = useState('');

  useEffect(() => {
    if (!start) return;
    
    let i = 0;
    const timer = setTimeout(() => {
      const interval = setInterval(() => {
        setDisplayed(text.substring(0, i));
        i++;
        if (i > text.length) {
          clearInterval(interval);
          onComplete?.();
        }
      }, 20);
      return () => clearInterval(interval);
    }, delay);
    
    return () => clearTimeout(timer);
  }, [text, delay, start, onComplete]);

  return <span>{displayed}{displayed.length < text.length && start && <span className="animate-pulse">|</span>}</span>;
};

const AIChatDemo = () => {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timer1 = setTimeout(() => setStep(1), 1000); // Start typing user query
    return () => clearTimeout(timer1);
  }, []);

  return (
    <div className="w-full h-full bg-[#111827]/50 rounded-2xl border border-[rgba(255,255,255,0.05)] p-4 flex flex-col font-sans relative overflow-hidden">
      {/* Fake Header */}
      <div className="flex items-center gap-2 pb-3 border-b border-[rgba(255,255,255,0.05)] mb-4">
        <div className="w-2 h-2 rounded-full bg-[var(--color-accent-emerald)]" />
        <span className="text-xs font-semibold text-[var(--color-text-secondary)]">HospitalIQ Assistant</span>
      </div>

      <div className="flex-1 flex flex-col space-y-4">
        {/* User Message */}
        {step >= 1 && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-end"
          >
            <div className="bg-[var(--color-surface-2)] text-[var(--color-text-primary)] rounded-2xl rounded-tr-sm px-4 py-3 text-sm shadow-lg max-w-[90%] border border-[var(--color-border-subtle)]">
              <TypewriterText 
                text="Assess cardiac risk for a 65yo in Mumbai" 
                start={step >= 1} 
                onComplete={() => setTimeout(() => setStep(2), 500)} 
              />
            </div>
          </motion.div>
        )}

        {/* AI Loading State */}
        {step === 2 && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-start"
          >
            <div className="flex space-x-1 px-4 py-3">
              <div className="w-2 h-2 rounded-full bg-[var(--color-accent-cyan)] animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 rounded-full bg-[var(--color-accent-cyan)] animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 rounded-full bg-[var(--color-accent-cyan)] animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </motion.div>
        )}

        {/* AI Response */}
        {step >= 3 && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-start flex-col items-start gap-2 max-w-[95%]"
          >
            <div className="pl-4 border-l-2 border-[var(--color-accent-cyan)] text-[var(--color-text-primary)] text-sm leading-relaxed">
              <TypewriterText 
                text="Based on real-time epidemiological data, patients fitting this profile in Mumbai currently face a HIGH risk factor. The Random Forest model indicates a 78% probability of acute complications. I recommend preemptive screening at Lilavati Hospital (currently 42% ICU capacity)." 
                start={step >= 3} 
                onComplete={() => setTimeout(() => setStep(4), 500)}
              />
            </div>
            
            {/* RAG Context Tags */}
            {step >= 4 && (
              <motion.div 
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex flex-wrap gap-2 mt-2 ml-4"
              >
                <span className="text-[10px] px-2 py-1 rounded bg-[var(--color-surface-2)] text-[var(--color-text-muted)] border border-[rgba(255,255,255,0.05)]">
                  Context: PatientRecords_Mumbai
                </span>
                <span className="text-[10px] px-2 py-1 rounded bg-[rgba(0,240,255,0.1)] text-[var(--color-accent-cyan)] border border-[rgba(0,240,255,0.2)]">
                  Model: Ensemble_RiskPredictor
                </span>
              </motion.div>
            )}
          </motion.div>
        )}
      </div>

      {/* Trigger state changes without being seen */}
      {step === 2 && <div className="hidden">{setTimeout(() => setStep(3), 1500)}</div>}
    </div>
  );
};

export default AIChatDemo;

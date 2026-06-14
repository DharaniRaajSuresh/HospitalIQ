import React from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

const CTASection = () => {
  const navigate = useNavigate();

  return (
    <section className="py-32 relative overflow-hidden w-full flex items-center justify-center">
      {/* Cinematic background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-to-br from-[#06b6d4] to-[#8b5cf6] rounded-full blur-[120px] opacity-20 pointer-events-none" />
      
      <div className="relative z-10 max-w-4xl mx-auto text-center px-6">
        <motion.h2 
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-5xl md:text-7xl font-bold text-[var(--color-text-primary)] mb-8 tracking-tight"
        >
          Ready to transform <br/>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#06b6d4] to-[#8b5cf6]">
            healthcare delivery?
          </span>
        </motion.h2>
        
        <motion.p 
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="text-xl text-[var(--color-text-secondary)] mb-12 max-w-2xl mx-auto"
        >
          Join hundreds of leading institutions using HospitalIQ to predict demand, allocate resources, and improve patient outcomes.
        </motion.p>
        
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          <button 
            onClick={() => navigate('/dashboard')}
            className="group relative px-10 py-5 rounded-full bg-white text-black font-bold text-xl overflow-hidden hover:scale-105 transition-transform duration-300"
          >
            <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-[#06b6d4] to-[#8b5cf6] opacity-0 group-hover:opacity-10 transition-opacity" />
            <span className="relative z-10 flex items-center gap-2">
              Launch Dashboard
              <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </span>
          </button>
        </motion.div>
      </div>
    </section>
  );
};

export default CTASection;

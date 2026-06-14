import React from 'react';
import { motion } from 'framer-motion';

const IndiaMapAnimation = () => {
  return (
    <div className="flex flex-col lg:flex-row items-center gap-16 w-full">
      <div className="flex-1 lg:pr-12">
        <h2 className="text-4xl md:text-5xl font-bold text-[var(--color-text-primary)] mb-6 leading-tight">
          National Risk Map
        </h2>
        <p className="text-xl text-[var(--color-text-secondary)] mb-8 font-light">
          Visualize healthcare demand and resource allocation across India in real-time. Identify critical hotspots before they reach capacity.
        </p>
        <ul className="space-y-4">
          {[
            "Real-time ICU bed availability",
            "Epidemiological trend tracking",
            "Resource reallocation suggestions"
          ].map((item, idx) => (
            <motion.li 
              key={idx}
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1 + 0.3 }}
              className="flex items-center text-[var(--color-text-primary)]"
            >
              <div className="w-2 h-2 rounded-full bg-[#10b981] mr-4 shadow-[0_0_10px_#10b981]" />
              {item}
            </motion.li>
          ))}
        </ul>
      </div>

      <div className="flex-1 relative w-full aspect-square max-w-lg perspective-[1000px]">
        {/* Abstract 3D-like map representation using layered CSS/SVGs */}
        <div className="absolute inset-0 bg-[#151c2c] rounded-full border border-[rgba(255,255,255,0.05)] overflow-hidden shadow-2xl flex items-center justify-center group">
          <motion.div
            initial={{ rotateX: 20, rotateY: -20, scale: 0.8 }}
            whileInView={{ rotateX: 0, rotateY: 0, scale: 1 }}
            transition={{ duration: 1.5, ease: "easeOut" }}
            className="relative w-full h-full flex items-center justify-center style-preserve-3d group-hover:rotate-y-[12deg] transition-transform duration-700"
          >
            {/* Base glowing grid */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(6,182,212,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.1)_1px,transparent_1px)] bg-[size:40px_40px] opacity-30" />
            
            {/* Simulated Data Nodes */}
            {[...Array(15)].map((_, i) => (
              <motion.div
                key={i}
                initial={{ scale: 0, opacity: 0 }}
                whileInView={{ scale: 1, opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.5 + Math.random(), duration: 0.5 }}
                className="absolute w-3 h-3 rounded-full bg-[#06b6d4] shadow-[0_0_15px_#06b6d4]"
                style={{
                  top: `${20 + Math.random() * 60}%`,
                  left: `${20 + Math.random() * 60}%`,
                }}
              >
                <div className="absolute inset-0 rounded-full border border-[#06b6d4] animate-ping opacity-75" />
              </motion.div>
            ))}
            
            {/* Central massive glowing hotspot */}
            <motion.div 
              animate={{ 
                boxShadow: ['0 0 20px rgba(16, 185, 129, 0.4)', '0 0 60px rgba(16, 185, 129, 0.8)', '0 0 20px rgba(16, 185, 129, 0.4)']
              }}
              transition={{ duration: 3, repeat: Infinity }}
              className="absolute w-8 h-8 rounded-full bg-[#10b981] top-[40%] left-[45%] z-10"
            />
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default IndiaMapAnimation;

import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';

const ScrollSection = ({ children, className = '', id }) => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: false, margin: "-10% 0px" });

  return (
    <section 
      id={id}
      ref={ref} 
      className={`min-h-screen w-full flex items-center justify-center relative overflow-hidden py-24 ${className}`}
    >
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 50 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-7xl mx-auto px-6 relative z-10"
      >
        {children}
      </motion.div>
    </section>
  );
};

export default ScrollSection;

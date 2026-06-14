import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

const HeroSection = () => {
  const navigate = useNavigate();
  const canvasRef = useRef(null);

  useEffect(() => {
    // Simple particle system for the background
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let particles = [];

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', resize);
    resize();

    for (let i = 0; i < 50; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        radius: Math.random() * 2 + 0.5,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        alpha: Math.random() * 0.5 + 0.1
      });
    }

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = 'rgba(11, 18, 32, 1)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      // Draw gradient orb
      const gradient = ctx.createRadialGradient(
        canvas.width / 2, canvas.height / 3, 0,
        canvas.width / 2, canvas.height / 3, canvas.width / 2
      );
      gradient.addColorStop(0, 'rgba(6, 182, 212, 0.15)'); // Cyan
      gradient.addColorStop(0.5, 'rgba(139, 92, 246, 0.05)'); // Violet
      gradient.addColorStop(1, 'transparent');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      particles.forEach(p => {
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(240, 242, 248, ${p.alpha})`;
        ctx.fill();
      });

      animationFrameId = requestAnimationFrame(render);
    };
    render();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <section className="relative h-screen w-full flex flex-col items-center justify-center overflow-hidden">
      <canvas ref={canvasRef} className="absolute inset-0 z-0" />
      
      <div className="relative z-10 text-center px-6 max-w-5xl mx-auto flex flex-col items-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.9, filter: 'blur(10px)' }}
          animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
          transition={{ duration: 1.2, ease: "easeOut" }}
          className="mb-8"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#151c2c] border border-[rgba(255,255,255,0.1)] backdrop-blur-md mb-8">
            <span className="w-2 h-2 rounded-full bg-[#06b6d4] animate-pulse" />
            <span className="text-sm font-medium text-[#94a3b8]">HospitalIQ Intelligence Platform v2.0</span>
          </div>
          
          <h1 className="text-6xl md:text-8xl lg:text-[96px] font-bold tracking-tight text-[#f0f2f8] leading-[1.1] mb-6">
            Healthcare Data.<br/>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#06b6d4] via-[#10b981] to-[#8b5cf6]">
              Redefined.
            </span>
          </h1>
        </motion.div>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4, ease: "easeOut" }}
          className="text-xl md:text-2xl text-[#94a3b8] max-w-2xl font-light mb-12"
        >
          Predictive mortality, national risk mapping, and an AI copilot. Experience the cinematic future of hospital intelligence.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6, ease: "easeOut" }}
          className="flex flex-col sm:flex-row gap-4"
        >
          <button 
            onClick={() => navigate('/dashboard')}
            className="px-8 py-4 rounded-full bg-[#f0f2f8] text-[#0B1220] font-semibold text-lg hover:scale-105 transition-transform duration-300 shadow-[0_0_30px_rgba(240,242,248,0.3)]"
          >
            Enter Dashboard
          </button>
          <button 
            onClick={() => document.getElementById('discover').scrollIntoView({ behavior: 'smooth' })}
            className="px-8 py-4 rounded-full bg-[rgba(255,255,255,0.05)] text-[#f0f2f8] font-semibold text-lg border border-[rgba(255,255,255,0.1)] hover:bg-[rgba(255,255,255,0.1)] transition-colors duration-300 backdrop-blur-sm"
          >
            Discover Platform
          </button>
        </motion.div>
      </div>
      
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5, duration: 1 }}
        className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-[#64748b]"
      >
        <span className="text-sm tracking-widest uppercase font-mono">Scroll to explore</span>
        <div className="w-[1px] h-12 bg-gradient-to-b from-current to-transparent" />
      </motion.div>
    </section>
  );
};

export default HeroSection;

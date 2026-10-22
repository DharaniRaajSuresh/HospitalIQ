import React, { useEffect, useRef, useState } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { Activity } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { GradientText } from './ui/GradientText';

const HeroSection = () => {
  const navigate = useNavigate();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const { scrollY } = useScroll();
  const y = useTransform(scrollY, [0, 1000], [0, 300]);
  const opacity = useTransform(scrollY, [0, 500], [1, 0]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    let animationFrameId: number;
    const particles: any[] = [];

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', resize);
    resize();

    // Create particles
    for (let i = 0; i < 100; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        radius: Math.random() * 2 + 0.5,
        baseX: Math.random() * canvas.width,
        baseY: Math.random() * canvas.height,
        density: (Math.random() * 30) + 1,
        alpha: Math.random() * 0.5 + 0.1
      });
    }

    let mouse = { x: -1000, y: -1000 };
    const handleCanvasMouse = (e: MouseEvent) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    };
    window.addEventListener('mousemove', handleCanvasMouse);

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // Draw massive background orb
      const orbX = canvas.width / 2 + (mouse.x - canvas.width / 2) * 0.05;
      const orbY = canvas.height / 3 + (mouse.y - canvas.height / 2) * 0.05;
      
      const gradient = ctx.createRadialGradient(orbX, orbY, 0, orbX, orbY, canvas.width * 0.6);
      gradient.addColorStop(0, 'rgba(0, 240, 255, 0.08)');
      gradient.addColorStop(0.5, 'rgba(176, 38, 255, 0.03)');
      gradient.addColorStop(1, 'transparent');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw and update particles
      particles.forEach(p => {
        const dx = mouse.x - p.x;
        const dy = mouse.y - p.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const forceDirectionX = dx / distance;
        const forceDirectionY = dy / distance;
        const maxDistance = 150;
        const force = (maxDistance - distance) / maxDistance;
        const directionX = forceDirectionX * force * p.density;
        const directionY = forceDirectionY * force * p.density;

        if (distance < maxDistance) {
          p.x -= directionX;
          p.y -= directionY;
        } else {
          if (p.x !== p.baseX) {
            const dx = p.x - p.baseX;
            p.x -= dx / 20;
          }
          if (p.y !== p.baseY) {
            const dy = p.y - p.baseY;
            p.y -= dy / 20;
          }
        }

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${p.alpha})`;
        ctx.fill();
      });

      animationFrameId = requestAnimationFrame(render);
    };
    render();

    return () => {
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', handleCanvasMouse);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <section ref={containerRef} className="relative h-screen w-full flex flex-col items-center justify-center overflow-hidden">


      <canvas ref={canvasRef} className="absolute inset-0 z-0" />
      
      <motion.div 
        style={{ y, opacity }}
        className="relative z-10 text-center px-6 max-w-5xl mx-auto flex flex-col items-center pt-20"
      >
        <motion.div
          initial={{ opacity: 0, y: 30, filter: 'blur(10px)' }}
          animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
          transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
          className="mb-8"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[var(--color-surface-2)] border border-[var(--color-border-subtle)] backdrop-blur-md mb-8 shadow-lg">
            <span className="w-2 h-2 rounded-full bg-[var(--color-accent-emerald)] animate-pulse shadow-[0_0_8px_rgba(0,255,157,0.8)]" />
            <span className="text-xs font-semibold text-[var(--color-text-secondary)] tracking-widest uppercase">
              Powered by 6 Ensemble ML Models
            </span>
          </div>
          
          <h1 className="text-6xl md:text-8xl lg:text-[100px] font-extrabold tracking-tighter text-[#f0f2f8] leading-[1.05] mb-6">
            Healthcare Data.<br/>
            <GradientText as="span" animate={true}>
              Redefined.
            </GradientText>
          </h1>
        </motion.div>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4, ease: "easeOut" }}
          className="text-lg md:text-2xl text-[var(--color-text-secondary)] max-w-2xl font-light mb-12"
        >
          Predictive mortality, national risk mapping, and an AI copilot. Experience the cinematic future of hospital intelligence.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6, ease: "easeOut" }}
          className="flex flex-col sm:flex-row gap-6 relative"
        >
          {/* Magnetic button effect */}
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            transition={{ type: "spring", stiffness: 400, damping: 10 }}
          >
            <button 
              onClick={() => navigate('/login')}
              className="relative group px-10 py-4 rounded-full bg-white text-[#0B1220] font-bold text-lg overflow-hidden shadow-[0_0_40px_rgba(0,240,255,0.3)]"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-[var(--color-accent-cyan)] to-[var(--color-accent-violet)] opacity-0 group-hover:opacity-10 transition-opacity duration-300" />
              <div className="absolute inset-0 -translate-x-[150%] skew-x-12 bg-gradient-to-r from-transparent via-white to-transparent opacity-40 group-hover:animate-[shine_1.5s_ease-in-out_infinite]" />
              <span className="relative">Get Started</span>
            </button>
          </motion.div>
          
          <button 
            onClick={() => document.getElementById('discover')?.scrollIntoView({ behavior: 'smooth' })}
            className="px-10 py-4 rounded-full bg-[rgba(255,255,255,0.03)] text-[#f0f2f8] font-semibold text-lg border border-[rgba(255,255,255,0.1)] hover:bg-[rgba(255,255,255,0.08)] transition-colors duration-300 backdrop-blur-sm"
          >
            Discover Platform
          </button>
        </motion.div>
      </motion.div>
      
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5, duration: 1 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-3 text-[var(--color-text-muted)]"
      >
        <span className="text-[10px] tracking-[0.2em] uppercase font-mono">Scroll to explore</span>
        <div className="w-[1px] h-16 bg-gradient-to-b from-current to-transparent animate-pulse" />
      </motion.div>

      <style>{`
        @keyframes shine {
          100% { transform: translateX(150%) skewX(12deg); }
        }
      `}</style>
    </section>
  );
};

export default HeroSection;

import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { Shield, Activity, Globe } from 'lucide-react';
import { GradientText } from './ui/GradientText';

export default function GovHero() {
  const containerRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.fromTo('.hero-badge', 
        { y: 20, opacity: 0 }, 
        { y: 0, opacity: 1, duration: 0.8, ease: "power3.out" }
      );
      
      gsap.fromTo('.hero-title', 
        { y: 30, opacity: 0 }, 
        { y: 0, opacity: 1, duration: 1, delay: 0.2, ease: "power3.out" }
      );
      
      gsap.fromTo('.hero-subtitle', 
        { y: 20, opacity: 0 }, 
        { y: 0, opacity: 1, duration: 1, delay: 0.4, ease: "power3.out" }
      );
      
      gsap.fromTo('.hero-stats', 
        { y: 20, opacity: 0 }, 
        { y: 0, opacity: 1, duration: 1, delay: 0.6, ease: "power3.out", stagger: 0.1 }
      );
    }, containerRef);
    
    return () => ctx.revert();
  }, []);

  return (
    <div ref={containerRef} className="relative min-h-screen flex items-center justify-center pt-20 overflow-hidden">
      {/* Background Grid & Glow */}
      <div className="absolute inset-0 bg-[#020617]">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-amber-500/10 rounded-full blur-[120px] pointer-events-none" />
      </div>

      <div className="relative z-10 container mx-auto px-6 flex flex-col items-center text-center">
        <div className="hero-badge inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/20 mb-8 backdrop-blur-sm">
          <Shield className="w-4 h-4 text-amber-400" />
          <span className="text-xs font-medium text-amber-400 uppercase tracking-widest">National Health Grid Command</span>
        </div>
        
        <h1 className="hero-title text-5xl md:text-7xl lg:text-8xl font-bold tracking-tighter text-white mb-6 max-w-5xl">
          Orchestrating <br/>
          <GradientText className="from-amber-400 via-orange-500 to-rose-500">
            Public Health at Scale
          </GradientText>
        </h1>
        
        <p className="hero-subtitle text-lg md:text-xl text-[var(--color-text-muted)] max-w-2xl mb-16 leading-relaxed">
          The unified intelligence platform for Ministries of Health, deploying 6-stage machine learning pipelines to preempt pandemics and distribute national healthcare resources.
        </p>
        
        {/* National Scale Stats */}
        <div className="flex flex-wrap justify-center gap-6 md:gap-12">
          <div className="hero-stats text-left">
            <div className="flex items-center gap-2 text-amber-400 mb-2">
              <Activity className="w-5 h-5" />
              <span className="text-sm font-mono uppercase tracking-wider">Live Monitoring</span>
            </div>
            <div className="text-4xl font-bold text-white font-mono">1.4B+</div>
            <div className="text-sm text-[var(--color-text-muted)]">Citizens Covered</div>
          </div>
          
          <div className="hero-stats w-px h-16 bg-[var(--color-border-subtle)] hidden md:block" />
          
          <div className="hero-stats text-left">
            <div className="flex items-center gap-2 text-amber-400 mb-2">
              <Globe className="w-5 h-5" />
              <span className="text-sm font-mono uppercase tracking-wider">Infrastructure</span>
            </div>
            <div className="text-4xl font-bold text-white font-mono">45,000+</div>
            <div className="text-sm text-[var(--color-text-muted)]">Hospitals Synced</div>
          </div>
        </div>
      </div>
      
      {/* Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 opacity-50">
        <span className="text-xs text-white uppercase tracking-widest font-mono">Discover</span>
        <div className="w-px h-12 bg-gradient-to-b from-amber-400 to-transparent" />
      </div>
    </div>
  );
}

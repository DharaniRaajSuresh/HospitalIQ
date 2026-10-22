import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Database, Network, Radar, Zap } from 'lucide-react';

export default function GovStickyFeatures() {
  const containerRef = useRef<HTMLDivElement>(null);
  const leftColRef = useRef<HTMLDivElement>(null);
  const rightColRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      // Pin the left column while the right column scrolls
      ScrollTrigger.create({
        trigger: containerRef.current,
        start: "top top",
        end: "bottom bottom",
        pin: leftColRef.current,
        pinSpacing: false,
      });

      // Animate cards as they enter viewport
      const cards = gsap.utils.toArray('.feature-card');
      cards.forEach((card: any) => {
        gsap.fromTo(card,
          { opacity: 0.2, scale: 0.95 },
          {
            opacity: 1, scale: 1,
            scrollTrigger: {
              trigger: card,
              start: "top center+=100",
              end: "center center",
              scrub: 0.5,
            }
          }
        );
      });
    }, containerRef);

    return () => ctx.revert();
  }, []);

  const features = [
    {
      icon: <Network className="w-8 h-8 text-amber-500" />,
      title: "Interstate Orchestration",
      desc: "Synchronize ICU bed availability and oxygen reserves across 28 states and 8 union territories in real-time."
    },
    {
      icon: <Radar className="w-8 h-8 text-rose-500" />,
      title: "Pandemic Early Warning",
      desc: "6-ML ensemble predicts outbreak clusters weeks before they hit critical mass, saving lives and resources."
    },
    {
      icon: <Database className="w-8 h-8 text-cyan-500" />,
      title: "Unified Health Records",
      desc: "Seamless integration of millions of patient histories, securely accessible by authorized personnel nationwide."
    },
    {
      icon: <Zap className="w-8 h-8 text-amber-400" />,
      title: "Automated Resource Allocation",
      desc: "Smart routing of emergency medical supplies using logistical algorithms based on real-time mortality predictors."
    }
  ];

  return (
    <section ref={containerRef} className="relative w-full max-w-7xl mx-auto px-6 py-24 flex flex-col md:flex-row items-start gap-12 lg:gap-24">
      {/* Left Pinned Column */}
      <div ref={leftColRef} className="w-full md:w-1/2 flex flex-col justify-center h-screen md:h-screen pt-20">
        <div className="inline-block px-3 py-1 mb-6 border border-amber-500/30 rounded-full bg-amber-500/10 text-xs font-mono text-amber-400 tracking-widest uppercase">
          Core Capabilities
        </div>
        <h2 className="text-4xl lg:text-6xl font-bold tracking-tight text-white mb-6">
          National Level <br />
          <span className="text-[var(--color-text-muted)]">Command & Control</span>
        </h2>
        <p className="text-lg text-[var(--color-text-muted)] leading-relaxed max-w-md">
          HospitalIQ equips government bodies with a bird's-eye view of the entire national health grid. Replace fragmented reporting with AI-driven, actionable intelligence.
        </p>
      </div>

      {/* Right Scrolling Column */}
      <div ref={rightColRef} className="w-full md:w-1/2 flex flex-col gap-12 pt-[50vh] pb-[50vh]">
        {features.map((f, i) => (
          <div key={i} className="feature-card relative bg-[#0B1220] border border-[rgba(255,255,255,0.05)] p-8 md:p-12 rounded-[2rem] overflow-hidden group">
            {/* Ambient glow */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/5 blur-[100px] rounded-full transition-opacity opacity-0 group-hover:opacity-100" />
            
            <div className="relative z-10">
              <div className="mb-6 p-4 inline-block rounded-2xl bg-[#020617] border border-[rgba(255,255,255,0.05)]">
                {f.icon}
              </div>
              <h3 className="text-2xl font-bold text-white mb-4">{f.title}</h3>
              <p className="text-[var(--color-text-muted)] leading-relaxed text-lg">
                {f.desc}
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

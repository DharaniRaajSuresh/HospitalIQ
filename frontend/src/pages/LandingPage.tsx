// @ts-nocheck
import React, { useEffect } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

import HeroSection from '../components/landing/HeroSection';
import ScrollSection from '../components/landing/ScrollSection';
import ScrollMetrics from '../components/landing/ScrollMetrics';
import IndiaMapAnimation from '../components/landing/IndiaMapAnimation';
import NeuralNetworkViz from '../components/landing/NeuralNetworkViz';
import AIChatDemo from '../components/landing/AIChatDemo';
import CTASection from '../components/landing/CTASection';

gsap.registerPlugin(ScrollTrigger);

const LandingPage = () => {
  useEffect(() => {
    // ScrollTrigger for background color shifts
    const sections = gsap.utils.toArray('.scroll-bg-shift');
    
    sections.forEach((sec) => {
      ScrollTrigger.create({
        trigger: sec,
        start: "top center",
        end: "bottom center",
        onEnter: () => gsap.to('body', { backgroundColor: 'var(--color-bg-primary)', duration: 1 }),
        onEnterBack: () => gsap.to('body', { backgroundColor: 'var(--color-bg-primary)', duration: 1 })
      });
    });

    return () => {
      ScrollTrigger.getAll().forEach(t => t.kill());
    };
  }, []);

  return (
    <div className="bg-[var(--color-bg-primary)] min-h-screen text-[var(--color-text-primary)] selection:bg-[var(--color-accent-cyan)] selection:text-white font-sans overflow-x-hidden">
      <HeroSection />
      
      <div id="discover" className="relative z-10 bg-[var(--color-bg-primary)] scroll-bg-shift">
        <ScrollSection id="metrics">
          <ScrollMetrics />
        </ScrollSection>
        
        <ScrollSection id="map-risk" className="bg-[var(--color-bg-secondary)] rounded-[3rem] my-12 mx-4 md:mx-12 shadow-2xl border border-[rgba(255,255,255,0.02)]">
          <IndiaMapAnimation />
        </ScrollSection>
        
        <ScrollSection id="mortality">
          <NeuralNetworkViz />
        </ScrollSection>

        <ScrollSection id="ai-copilot" className="bg-[var(--color-bg-secondary)] rounded-[3rem] my-12 mx-4 md:mx-12 shadow-2xl border border-[rgba(255,255,255,0.02)]">
          <AIChatDemo />
        </ScrollSection>
        
        <CTASection />
      </div>
    </div>
  );
};

export default LandingPage;


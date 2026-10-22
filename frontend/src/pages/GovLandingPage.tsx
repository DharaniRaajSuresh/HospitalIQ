import React, { useEffect } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ReactLenis } from 'lenis/react';

import GovHero from '../components/landing/GovHero';
import GovStickyFeatures from '../components/landing/GovStickyFeatures';
import GovImpactCalculator from '../components/landing/GovImpactCalculator';
import GovSecurity from '../components/landing/GovSecurity';
import GovCTASection from '../components/landing/GovCTASection';
import { CustomCursor } from '../components/landing/ui/CustomCursor';

gsap.registerPlugin(ScrollTrigger);

export default function GovLandingPage() {
  useEffect(() => {
    // ScrollTrigger for background color shifts
    const sections = gsap.utils.toArray('.scroll-bg-shift');
    
    sections.forEach((sec: any) => {
      ScrollTrigger.create({
        trigger: sec,
        start: "top center",
        end: "bottom center",
        onEnter: () => gsap.to('body', { backgroundColor: '#020617', duration: 1 }), // darker blue/slate
        onEnterBack: () => gsap.to('body', { backgroundColor: '#020617', duration: 1 })
      });
    });

    return () => {
      ScrollTrigger.getAll().forEach(t => t.kill());
    };
  }, []);

  return (
    <ReactLenis root options={{ lerp: 0.05, smoothWheel: true }}>
      <div className="bg-[#020617] min-h-screen text-[var(--color-text-primary)] selection:bg-[var(--color-accent-amber)] selection:text-black font-sans overflow-x-hidden">
        <CustomCursor />
        
        {/* Navigation Bar (Simple) */}
        <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4 md:px-12 backdrop-blur-md border-b border-[rgba(255,255,255,0.05)] bg-[#020617]/50">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded bg-gradient-to-br from-amber-400 to-orange-600 flex items-center justify-center">
              <span className="text-white font-bold text-lg leading-none">H</span>
            </div>
            <span className="text-lg font-semibold tracking-tight text-white">HospitalIQ <span className="text-[var(--color-text-muted)] font-normal">| National Command</span></span>
          </div>
          <div className="flex items-center gap-4">
            <a href="/" className="text-sm text-[var(--color-text-muted)] hover:text-white transition-colors">Enterprise</a>
            <a href="/login" className="px-4 py-2 text-sm font-medium text-black bg-amber-400 hover:bg-amber-300 rounded-full transition-colors">Access Portal</a>
          </div>
        </nav>

        <GovHero />
        
        <div className="relative z-10 bg-[#020617] scroll-bg-shift pb-24">
          <GovStickyFeatures />
          <GovImpactCalculator />
          <GovSecurity />
        </div>
        
        <GovCTASection />
      </div>
    </ReactLenis>
  );
}

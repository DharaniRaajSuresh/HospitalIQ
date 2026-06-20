import React, { useEffect, Suspense, lazy } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ReactLenis } from 'lenis/react';

import HeroSection from '../components/landing/HeroSection';
import ScrollSection from '../components/landing/ScrollSection';
import ScrollMetrics from '../components/landing/ScrollMetrics';
import CTASection from '../components/landing/CTASection';
import { CustomCursor } from '../components/landing/ui/CustomCursor';
import { BentoGrid, BentoGridItem } from '../components/landing/ui/BentoGrid';
import { GradientText } from '../components/landing/ui/GradientText';

// Lazy load heavy components
const IndiaMapAnimation = lazy(() => import('../components/landing/IndiaMapAnimation'));
const NeuralNetworkViz = lazy(() => import('../components/landing/NeuralNetworkViz'));
const AIChatDemo = lazy(() => import('../components/landing/AIChatDemo'));

gsap.registerPlugin(ScrollTrigger);

const LoadingFallback = () => (
  <div className="flex items-center justify-center w-full h-64 bg-[rgba(255,255,255,0.02)] rounded-[2rem] border border-[rgba(255,255,255,0.05)]">
    <div className="w-8 h-8 rounded-full border-2 border-[var(--color-accent-cyan)] border-t-transparent animate-spin" />
  </div>
);

const LandingPage = () => {
  useEffect(() => {
    // ScrollTrigger for background color shifts
    const sections = gsap.utils.toArray('.scroll-bg-shift');
    
    sections.forEach((sec: any) => {
      ScrollTrigger.create({
        trigger: sec,
        start: "top center",
        end: "bottom center",
        onEnter: () => gsap.to('body', { backgroundColor: 'var(--landing-bg-dark)', duration: 1 }),
        onEnterBack: () => gsap.to('body', { backgroundColor: 'var(--landing-bg-dark)', duration: 1 })
      });
    });

    return () => {
      ScrollTrigger.getAll().forEach(t => t.kill());
    };
  }, []);

  return (
    <ReactLenis root options={{ lerp: 0.05, smoothWheel: true }}>
      <div className="bg-[var(--landing-bg-dark)] min-h-screen text-[var(--color-text-primary)] selection:bg-[var(--color-accent-cyan)] selection:text-white font-sans overflow-x-hidden">
        <CustomCursor />
        <HeroSection />
        
        <div id="discover" className="relative z-10 bg-[var(--landing-bg-dark)] scroll-bg-shift pb-24">
          <ScrollSection id="metrics">
            <ScrollMetrics />
          </ScrollSection>
          
          <ScrollSection id="map-risk" className="bg-[var(--landing-glass-bg)] rounded-[3rem] my-12 mx-4 md:mx-12 shadow-2xl border border-[var(--landing-glass-border)] overflow-hidden">
            <Suspense fallback={<LoadingFallback />}>
              <IndiaMapAnimation />
            </Suspense>
          </ScrollSection>
          
          {/* Bento Box Layout for ML & AI */}
          <ScrollSection id="tech-stack" className="my-24 px-4 md:px-12">
            <div className="text-center mb-16">
              <div className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-full bg-[var(--color-surface-2)] border border-[var(--color-border-subtle)] mb-4">
                <span className="w-2 h-2 rounded-full bg-[var(--color-accent-violet)] animate-pulse" />
                <span className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider">Core Intelligence</span>
              </div>
              <GradientText as="h2" className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
                6-Model Ensemble Architecture
              </GradientText>
              <p className="text-[var(--color-text-muted)] max-w-2xl mx-auto text-lg">
                Orchestrating Gradient Boosting, Random Forests, and LLMs to process millions of healthcare data points in real-time.
              </p>
            </div>

            <BentoGrid>
              {/* Box 1: AI Chat (Top Left) */}
              <BentoGridItem className="md:col-span-1">
                <h3 className="text-xl font-semibold mb-2">Generative Copilot</h3>
                <p className="text-sm text-[var(--color-text-muted)] mb-6">Ask complex questions, get data-backed answers instantly.</p>
                <div className="flex-1 min-h-[300px]">
                  <Suspense fallback={<LoadingFallback />}>
                    <AIChatDemo />
                  </Suspense>
                </div>
              </BentoGridItem>

              {/* Box 2: Neural Net (Top Right, Wide) */}
              <BentoGridItem className="md:col-span-2">
                <h3 className="text-xl font-semibold mb-2">Predictive Forecasting</h3>
                <p className="text-sm text-[var(--color-text-muted)] mb-6">Visualizing future bed demands with 95% confidence intervals.</p>
                <div className="flex-1 min-h-[300px] flex items-center justify-center relative">
                  <div className="absolute inset-0 bg-gradient-to-t from-[#0B1220] to-transparent z-10 pointer-events-none" />
                  <Suspense fallback={<LoadingFallback />}>
                    <NeuralNetworkViz />
                  </Suspense>
                </div>
              </BentoGridItem>
            </BentoGrid>
          </ScrollSection>
          
          <CTASection />
        </div>
      </div>
    </ReactLenis>
  );
};

export default LandingPage;

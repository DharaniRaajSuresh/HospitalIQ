import React from 'react';
import { ShieldAlert, ArrowRight } from 'lucide-react';

export default function GovCTASection() {
  return (
    <section className="relative py-32 overflow-hidden border-t border-[rgba(255,255,255,0.05)]">
      {/* Background elements */}
      <div className="absolute inset-0 bg-[#0B1220]" />
      <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-[0.03]" />
      
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-amber-500/10 blur-[120px] rounded-full pointer-events-none" />

      <div className="relative z-10 max-w-4xl mx-auto px-6 text-center">
        <div className="inline-flex items-center justify-center p-4 rounded-full bg-amber-500/10 border border-amber-500/20 mb-8">
          <ShieldAlert className="w-8 h-8 text-amber-500" />
        </div>
        
        <h2 className="text-4xl md:text-6xl font-bold text-white mb-6 tracking-tight">
          Ready to Modernize the <br className="hidden md:block" />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-rose-500">
            National Health Grid?
          </span>
        </h2>
        
        <p className="text-xl text-[var(--color-text-muted)] mb-12 max-w-2xl mx-auto">
          Equip your state's Ministry of Health with real-time analytics, predictive modeling, and absolute operational transparency.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <a href="/login" className="group flex items-center justify-center gap-2 w-full sm:w-auto px-8 py-4 bg-amber-500 hover:bg-amber-400 text-black font-semibold rounded-full transition-all text-lg hover:scale-105 active:scale-95 shadow-[0_0_40px_rgba(245,158,11,0.3)]">
            Deploy Infrastructure
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </a>
          <a href="/login" className="flex items-center justify-center w-full sm:w-auto px-8 py-4 bg-[#020617] hover:bg-[#0B1220] border border-[rgba(255,255,255,0.1)] text-white font-medium rounded-full transition-colors text-lg">
            Request Gov Demo
          </a>
        </div>
      </div>
    </section>
  );
}

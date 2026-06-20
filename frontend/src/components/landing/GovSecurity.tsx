import React from 'react';
import { Lock, ShieldCheck, FileCheck, Server } from 'lucide-react';

export default function GovSecurity() {
  const securityFeatures = [
    {
      icon: <ShieldCheck className="w-6 h-6 text-emerald-400" />,
      title: "Military-Grade Encryption",
      desc: "AES-256 bit encryption at rest and TLS 1.3 in transit ensures citizen health data is impenetrably secured."
    },
    {
      icon: <FileCheck className="w-6 h-6 text-amber-400" />,
      title: "HIPAA & NDHM Compliant",
      desc: "Fully compliant with global health data standards and the National Digital Health Mission architecture."
    },
    {
      icon: <Lock className="w-6 h-6 text-cyan-400" />,
      title: "Zero-Trust Architecture",
      desc: "Strict IAM roles and continuous authentication verify every request, regardless of origin."
    },
    {
      icon: <Server className="w-6 h-6 text-rose-400" />,
      title: "Data Sovereignty",
      desc: "100% locally hosted on sovereign cloud infrastructure, ensuring no cross-border data leakage."
    }
  ];

  return (
    <section className="w-full max-w-7xl mx-auto px-6 py-24 border-t border-[rgba(255,255,255,0.05)]">
      <div className="text-center mb-16">
        <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-white mb-6">
          Uncompromising <span className="text-emerald-400">Security</span>
        </h2>
        <p className="text-[var(--color-text-muted)] text-lg max-w-2xl mx-auto">
          Built from the ground up for government scale, HospitalIQ treats national health data as critical infrastructure.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {securityFeatures.map((feat, idx) => (
          <div key={idx} className="bg-[#0B1220] border border-[rgba(255,255,255,0.05)] p-6 rounded-2xl flex flex-col items-center text-center hover:-translate-y-2 transition-transform duration-300">
            <div className="w-16 h-16 rounded-full bg-[#020617] border border-[rgba(255,255,255,0.05)] flex items-center justify-center mb-6">
              {feat.icon}
            </div>
            <h3 className="text-lg font-bold text-white mb-3">{feat.title}</h3>
            <p className="text-sm text-[var(--color-text-muted)] leading-relaxed">{feat.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

const NeuralNetworkViz = () => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationId;
    
    // Setup nodes
    const nodes = [];
    const numNodes = 40;
    
    const resize = () => {
      if (canvas.parentElement) {
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = canvas.parentElement.clientHeight;
      }
    };
    
    resize();
    window.addEventListener('resize', resize);
    
    for(let i=0; i<numNodes; i++) {
      nodes.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.8,
        vy: (Math.random() - 0.5) * 0.8,
        radius: Math.random() * 2 + 1.5,
        color: Math.random() > 0.5 ? '#8b5cf6' : '#06b6d4'
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // Update and draw connections
      for(let i=0; i<numNodes; i++) {
        for(let j=i+1; j<numNodes; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx*dx + dy*dy);
          
          if(dist < 100) {
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.strokeStyle = `rgba(139, 92, 246, ${1 - dist/100})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
      
      // Update and draw nodes
      nodes.forEach(node => {
        node.x += node.vx;
        node.y += node.vy;
        
        if(node.x < 0 || node.x > canvas.width) node.vx *= -1;
        if(node.y < 0 || node.y > canvas.height) node.vy *= -1;
        
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = node.color;
        ctx.fill();
        ctx.shadowBlur = 10;
        ctx.shadowColor = node.color;
      });
      
      animationId = requestAnimationFrame(draw);
    };
    
    draw();
    
    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationId);
    };
  }, []);

  return (
    <div className="flex flex-col-reverse lg:flex-row items-center gap-16 w-full">
      <div className="flex-1 relative w-full h-[400px] md:h-[500px] bg-[#111827] rounded-3xl border border-[rgba(255,255,255,0.05)] overflow-hidden">
        <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#111827] to-transparent opacity-50" />
      </div>

      <div className="flex-1 lg:pl-12">
        <h2 className="text-4xl md:text-5xl font-bold text-[var(--color-text-primary)] mb-6 leading-tight">
          Predict Mortality.<br/>Save Lives.
        </h2>
        <p className="text-xl text-[var(--color-text-secondary)] mb-8 font-light">
          Our advanced neural networks analyze patient vitals, history, and demographics to provide accurate risk stratification upon admission.
        </p>
        <div className="grid grid-cols-2 gap-6">
          <div className="p-4 rounded-2xl bg-[var(--color-bg-card)] border border-[rgba(255,255,255,0.02)]">
            <div className="text-3xl font-bold text-[#8b5cf6] mb-2">ML</div>
            <div className="text-sm text-[var(--color-text-secondary)]">Driven by clinical data</div>
          </div>
          <div className="p-4 rounded-2xl bg-[var(--color-bg-card)] border border-[rgba(255,255,255,0.02)]">
            <div className="text-3xl font-bold text-[#06b6d4] mb-2">99%</div>
            <div className="text-sm text-[var(--color-text-secondary)]">Uptime and reliability</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NeuralNetworkViz;

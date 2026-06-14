import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, X, MessageSquare, Send } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function FloatingCopilot() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Floating Button */}
      <motion.button
        className="fixed bottom-6 right-6 z-50 p-4 rounded-full bg-gradient-to-r from-[var(--color-accent-violet)] to-[var(--color-accent-blue)] text-white shadow-[var(--shadow-glow-violet)] hover:shadow-[var(--shadow-lg)] transition-shadow"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(true)}
      >
        <Sparkles className="w-6 h-6" />
      </motion.button>

      {/* Mini Chat Window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            className="fixed bottom-24 right-6 w-80 sm:w-96 bg-[var(--color-bg-card)]/95 backdrop-blur-xl border border-[var(--color-border)] rounded-2xl shadow-2xl z-50 flex flex-col overflow-hidden"
          >
            <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-bg-elevated)]">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[var(--color-accent-violet)] to-[var(--color-accent-cyan)] flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-white">Assistant Chatbot</h4>
                  <p className="text-xs text-[var(--color-accent-cyan)]">Online</p>
                </div>
              </div>
              <button 
                onClick={() => setIsOpen(false)}
                className="p-1.5 rounded-md hover:bg-[var(--color-bg-primary)] text-[var(--color-text-secondary)] hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            
            <div className="h-64 p-4 overflow-y-auto bg-[var(--color-bg-primary)]">
              <div className="flex gap-3">
                <div className="w-6 h-6 rounded-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] flex items-center justify-center flex-shrink-0 mt-1">
                  <Sparkles className="w-3 h-3 text-[var(--color-accent-cyan)]" />
                </div>
                <div className="bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-2xl rounded-tl-sm px-4 py-2.5 text-xs text-[var(--color-text-primary)] leading-relaxed">
                  Hi! I'm your assistant. I can help you navigate the dashboard or answer quick questions about the data.
                </div>
              </div>
            </div>

            <div className="p-3 border-t border-[var(--color-border)] bg-[var(--color-bg-elevated)] flex flex-col gap-2">
              <div className="relative">
                <input 
                  type="text" 
                  placeholder="Ask a quick question..." 
                  className="w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-xl py-2 pl-3 pr-10 text-xs text-white focus:outline-none focus:border-[var(--color-accent-violet)]"
                />
                <button className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-accent-violet)] transition-colors">
                  <Send className="w-3 h-3" />
                </button>
              </div>
              <div className="flex justify-between items-center px-1">
                <span className="text-[10px] text-[var(--color-text-muted)]">Press Enter to send</span>
                <Link 
                  to="/dashboard/ai" 
                  onClick={() => setIsOpen(false)}
                  className="text-[10px] text-[var(--color-accent-cyan)] hover:underline flex items-center gap-1"
                >
                  <MessageSquare className="w-3 h-3" /> Open full chat
                </Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

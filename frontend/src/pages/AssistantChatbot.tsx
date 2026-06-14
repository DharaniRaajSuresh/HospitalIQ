// @ts-nocheck
import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Send, Bot, User, Sparkles, Command } from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';
import MarkdownRenderer from '../components/MarkdownRenderer';
import { getSuggestions, chatAI } from '../api';

const DEFAULT_SUGGESTIONS = [
  "Which hospital has the best success rate for cardiac disease?",
  "Which districts in Tamil Nadu have critical mortality risk?",
  "How many ICU beds are available across India?",
  "Compare government vs private hospitals for diabetes treatment",
  "Which state has the highest hospital bed shortage?",
  "What is the average hospital stay duration in India?",
];

export default function AssistantChatbot() {
  const [messages, setMessages] = useState([
    { id: 1, role: 'assistant', text: 'Hello! I can answer any question — healthcare data analysis, general knowledge, or anything else. What would you like to know?' }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [suggestions, setSuggestions] = useState(DEFAULT_SUGGESTIONS);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    getSuggestions().then(setSuggestions).catch(e => console.warn('Failed to load suggestions:', e));
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async (text = input) => {
    if (!text.trim()) return;
    
    const newMsg = { id: Date.now(), role: 'user', text };
    setMessages(prev => [...prev, newMsg]);
    setInput('');
    setIsTyping(true);

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 90000);
      const data = await chatAI(text, 'copilot-' + Date.now(), controller.signal);
      clearTimeout(timeout);
      setIsTyping(false);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        text: data.response || 'Sorry, I could not process that.'
      }]);
    } catch (err) {
      setIsTyping(false);
      const msg = err.name === 'AbortError'
        ? 'Request timed out. The AI model took too long — try again or ask something simpler.'
        : 'Service temporarily unavailable. Make sure the backend server is running (port 8000).';
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        text: msg
      }]);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] max-w-4xl mx-auto w-full space-y-4">
      <div className="text-center mb-2">
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center justify-center gap-2">
          <Sparkles className="w-6 h-6 text-[var(--color-accent-violet)]" />
          Assistant Chatbot
        </h1>
        <p className="text-[var(--color-text-secondary)] text-sm mt-1">Ask anything — healthcare data or general questions.</p>
      </div>

      <GlassCard className="flex-1 flex flex-col overflow-hidden border border-[var(--color-border)] bg-[var(--color-bg-card)]/50 backdrop-blur-xl shadow-2xl">
        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
          {messages.map((msg) => (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              key={msg.id} 
              className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1 ${
                msg.role === 'user' 
                  ? 'bg-gradient-to-tr from-[var(--color-accent-violet)] to-[var(--color-accent-cyan)]' 
                  : 'bg-[var(--color-bg-elevated)] border border-[var(--color-border)]'
              }`}>
                {msg.role === 'user' ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-[var(--color-accent-cyan)]" />}
              </div>
              <div className={`max-w-[80%] rounded-2xl px-5 py-3.5 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-[var(--color-accent-blue)] text-white'
                  : 'bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] border border-[var(--color-border)]'
              }`}>
                {msg.role === 'assistant' ? <MarkdownRenderer text={msg.text} /> : msg.text}
              </div>
            </motion.div>
          ))}
          
          {isTyping && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-4 flex-row">
              <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1 bg-[var(--color-bg-elevated)] border border-[var(--color-border)]">
                <Bot className="w-4 h-4 text-[var(--color-accent-cyan)]" />
              </div>
              <div className="bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-2xl px-5 py-4 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-[var(--color-accent-cyan)] rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-1.5 h-1.5 bg-[var(--color-accent-cyan)] rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-1.5 h-1.5 bg-[var(--color-accent-cyan)] rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </div>
            </motion.div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggestions */}
        {messages.length === 1 && (
          <div className="px-6 py-2 flex flex-wrap gap-2">
            {(suggestions.length > 0 ? suggestions : DEFAULT_SUGGESTIONS).map((sug, idx) => (
              <button 
                key={idx}
                onClick={() => handleSend(sug)}
                className="text-xs px-3 py-1.5 rounded-full border border-[var(--color-border)] bg-[var(--color-bg-primary)] text-[var(--color-text-secondary)] hover:text-white hover:border-[var(--color-accent-violet)] transition-colors"
              >
                {sug}
              </button>
            ))}
          </div>
        )}

        {/* Input Area */}
        <div className="p-4 border-t border-[var(--color-border)] bg-[var(--color-bg-primary)]/80">
          <form 
            onSubmit={(e) => { e.preventDefault(); handleSend(); }}
            className="relative flex items-center"
          >
            <Command className="w-4 h-4 absolute left-4 text-[var(--color-text-muted)]" />
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything about your data..."
              className="w-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-xl py-3 pl-11 pr-12 text-sm text-white focus:outline-none focus:border-[var(--color-accent-violet)] focus:ring-1 focus:ring-[var(--color-accent-violet)] shadow-inner transition-all"
            />
            <button
              type="submit"
              disabled={!input.trim() || isTyping}
              className="absolute right-2 p-2 rounded-lg bg-[var(--color-accent-violet)] text-white hover:bg-[#7c3aed] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
          <div className="text-center mt-2">
            <span className="text-[10px] text-[var(--color-text-muted)]">AI can make mistakes. Verify critical data via primary reports.</span>
          </div>
        </div>
      </GlassCard>
    </div>
  );
}

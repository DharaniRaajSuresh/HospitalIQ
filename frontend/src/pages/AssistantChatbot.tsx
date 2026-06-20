import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Bot, User, Sparkles, Plus, MessageSquare, Trash2, Copy, ThumbsUp, ThumbsDown, Clock } from 'lucide-react';
import MarkdownRenderer from '../components/MarkdownRenderer';
import { getSuggestions, chatAI } from '../api';
import Button from '../components/ui/Button';

interface Message {
  id: number;
  role: 'user' | 'assistant';
  text: string;
}

interface Session {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
}

const DEFAULT_SUGGESTIONS = [
  "Which hospital has the best success rate for cardiac disease?",
  "Which districts in Tamil Nadu have critical mortality risk?",
  "How many ICU beds are available across India?",
  "Compare government vs private hospitals for diabetes treatment",
  "Which state has the highest hospital bed shortage?",
  "What is the average hospital stay duration in India?",
];

const TOPIC_TAGS = [
  { label: 'Hospitals', color: 'var(--color-accent-cyan)' },
  { label: 'Mortality', color: 'var(--color-accent-rose)' },
  { label: 'Beds', color: 'var(--color-accent-emerald)' },
  { label: 'Diseases', color: 'var(--color-accent-amber)' },
  { label: 'Forecast', color: 'var(--color-accent-violet)' },
];

function getTimeBucket(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  if (diffDays < 1) return 'Today';
  if (diffDays < 7) return 'This Week';
  return 'Earlier';
}

function groupSessions(sessions: Session[]): Record<string, Session[]> {
  const groups: Record<string, Session[]> = { Today: [], 'This Week': [], Earlier: [] };
  for (const s of sessions) {
    const bucket = getTimeBucket(s.createdAt);
    groups[bucket].push(s);
  }
  return groups;
}

export default function AssistantChatbot() {
  useEffect(() => { document.title = 'AI Assistant | HOSPi'; }, []);
  const [sessions, setSessions] = useState<Session[]>([
    { id: 'default', title: 'New Chat', messages: [{ id: 1, role: 'assistant', text: 'Hello! I can answer any question — healthcare data analysis, general knowledge, or anything else. What would you like to know?' }], createdAt: new Date() }
  ]);
  const [currentSessionId, setCurrentSessionId] = useState('default');
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>(DEFAULT_SUGGESTIONS);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const currentSession = sessions.find(s => s.id === currentSessionId) || sessions[0];
  const messages = currentSession?.messages || [];
  const grouped = groupSessions(sessions);

  useEffect(() => {
    getSuggestions<string[]>().then(setSuggestions).catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const createSession = () => {
    const id = 'session-' + Date.now();
    const newSession: Session = {
      id,
      title: 'New Chat',
      messages: [{ id: 1, role: 'assistant', text: 'Hello! I can answer any question. What would you like to know?' }],
      createdAt: new Date(),
    };
    setSessions(prev => [newSession, ...prev]);
    setCurrentSessionId(id);
    setTimeout(scrollToBottom, 0);
  };

  const deleteSession = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setSessions(prev => prev.filter(s => s.id !== id));
    if (currentSessionId === id) {
      setCurrentSessionId(sessions.find(s => s.id !== id)?.id || 'default');
    }
  };

  const handleSend = async (text: string = input) => {
    if (!text.trim() || isTyping) return;

    setSessions(prev => prev.map(s => {
      if (s.id !== currentSessionId) return s;
      const userMsg: Message = { id: Date.now(), role: 'user', text };
      const title = s.messages.length <= 1 ? text.slice(0, 50) + (text.length > 50 ? '...' : '') : s.title;
      return { ...s, title, messages: [...s.messages, userMsg] };
    }));
    setInput('');
    setIsTyping(true);

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 90000);
      const data = await chatAI(text, 'copilot-' + Date.now(), controller.signal);
      clearTimeout(timeout);
      setIsTyping(false);
      setSessions(prev => prev.map(s => {
        if (s.id !== currentSessionId) return s;
        return { ...s, messages: [...s.messages, { id: Date.now() + 1, role: 'assistant', text: (data as any).response || 'Sorry, I could not process that.' }] };
      }));
    } catch (err: any) {
      setIsTyping(false);
      const msg = err.name === 'AbortError'
        ? 'Request timed out. The AI model took too long — try again or ask something simpler.'
        : 'Service temporarily unavailable. Make sure the backend server is running (port 8000).';
      setSessions(prev => prev.map(s => {
        if (s.id !== currentSessionId) return s;
        return { ...s, messages: [...s.messages, { id: Date.now() + 1, role: 'assistant', text: msg }] };
      }));
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const adjustTextarea = () => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
    }
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      {/* Left Pane: Sessions + Suggestions */}
      <div className="w-[280px] flex-shrink-0 flex flex-col gap-3">
        <Button variant="primary" className="w-full justify-center" icon={Plus} onClick={createSession}>
          New Chat
        </Button>

        <div className="flex flex-col gap-2 px-1">
          {(['Today', 'This Week', 'Earlier'] as const).map(bucket => {
            const items = grouped[bucket];
            if (!items?.length) return null;
            return (
              <div key={bucket}>
                <p className="text-xs font-mono text-[var(--color-text-muted)] uppercase tracking-wider mb-1.5 px-2">{bucket}</p>
                <div className="space-y-0.5">
                  {items.map(session => (
                    <button key={session.id} onClick={() => setCurrentSessionId(session.id)}
                      className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left transition-colors ${session.id === currentSessionId ? 'bg-[var(--color-surface-2)] border border-[var(--color-border-subtle)]' : 'hover:bg-[var(--color-surface-2)]/50 text-[var(--color-text-muted)]'}`}>
                      <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
                      <span className="truncate flex-1">{session.title}</span>
                      {sessions.length > 1 && (
                        <Trash2 className="w-3 h-3 flex-shrink-0 opacity-0 hover:opacity-100 text-[var(--color-text-muted)] hover:text-[var(--color-accent-rose)] transition-all" onClick={e => deleteSession(e, session.id)} />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-auto space-y-3">
          <div>
            <p className="text-xs font-mono text-[var(--color-text-muted)] uppercase tracking-wider mb-2 px-2">Quick Topics</p>
            <div className="flex flex-wrap gap-1.5 px-2">
              {TOPIC_TAGS.map(tag => (
                <button key={tag.label} onClick={() => handleSend(`Tell me about ${tag.label.toLowerCase()}`)}
                  className="px-2.5 py-1 text-xs font-mono rounded-full border border-[var(--color-border-subtle)] text-[var(--color-text-muted)] hover:text-white hover:border-[var(--color-border-strong)] transition-colors"
                  style={{ '--dot-color': tag.color } as React.CSSProperties}>
                  <span className="inline-block w-1.5 h-1.5 rounded-full mr-1" style={{ backgroundColor: tag.color }} />
                  {tag.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="text-xs font-mono text-[var(--color-text-muted)] uppercase tracking-wider mb-2 px-2">Suggested</p>
            <div className="flex flex-col gap-1 px-2">
              {suggestions.slice(0, 4).map((sug, i) => (
                <button key={i} onClick={() => handleSend(sug)}
                  className="text-xs px-2.5 py-1.5 rounded-lg text-left text-[var(--color-text-muted)] hover:text-white hover:bg-[var(--color-surface-2)] transition-colors border border-transparent hover:border-[var(--color-border-subtle)]">
                  {sug}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Right Pane: Conversation */}
      <div className="flex-1 flex flex-col rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-1)] overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-2 px-5 py-3 border-b border-[var(--color-border-subtle)]">
          <Bot className="w-4 h-4 text-[var(--color-accent-cyan)]" />
          <span className="text-sm font-semibold text-white">AI Assistant</span>
          <span className="text-xs text-[var(--color-text-muted)] font-mono">{messages.length} messages</span>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length <= 1 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Sparkles className="w-10 h-10 text-[var(--color-accent-violet)] mb-3 opacity-50" />
              <p className="text-base text-[var(--color-text-primary)] font-medium">How can I help you today?</p>
              <p className="text-sm text-[var(--color-text-muted)] mt-1 max-w-sm">Ask about hospital data, disease outbreaks, bed availability, or anything healthcare-related.</p>
              <div className="flex gap-2 mt-4 flex-wrap justify-center">
                {DEFAULT_SUGGESTIONS.slice(0, 3).map((sug, i) => (
                  <button key={i} onClick={() => handleSend(sug)}
                    className="text-sm px-3 py-1.5 rounded-full border border-[var(--color-border-subtle)] text-[var(--color-text-muted)] hover:text-white hover:border-[var(--color-accent-cyan)] transition-colors">
                    {sug}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map(msg => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${msg.role === 'user' ? 'bg-[var(--color-accent-violet)]' : 'bg-[var(--color-surface-2)] border border-[var(--color-border-subtle)]'}`}>
                {msg.role === 'user' ? <User className="w-3.5 h-3.5 text-white" /> : <Bot className="w-3.5 h-3.5 text-[var(--color-accent-cyan)]" />}
              </div>
              <div className={`max-w-[75%] space-y-1 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`rounded-2xl px-4 py-3 text-base leading-relaxed ${msg.role === 'user' ? 'bg-[var(--color-surface-3)] text-white rounded-tr-md' : 'bg-[var(--color-surface-2)] text-[var(--color-text-primary)] border border-[var(--color-border-subtle)] rounded-tl-md border-l-2 border-l-[var(--color-accent-cyan)]'}`}>
                  {msg.role === 'assistant' ? <MarkdownRenderer text={msg.text} /> : msg.text}
                </div>
                {msg.role === 'assistant' && (
                  <div className="flex items-center gap-2 px-1">
                    <button className="text-[var(--color-text-muted)] hover:text-white transition-colors" title="Copy"><Copy className="w-3 h-3" /></button>
                    <button className="text-[var(--color-text-muted)] hover:text-emerald-400 transition-colors" title="Helpful"><ThumbsUp className="w-3 h-3" /></button>
                    <button className="text-[var(--color-text-muted)] hover:text-rose-400 transition-colors" title="Not helpful"><ThumbsDown className="w-3 h-3" /></button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex gap-3">
              <div className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 bg-[var(--color-surface-2)] border border-[var(--color-border-subtle)]">
                <Bot className="w-3.5 h-3.5 text-[var(--color-accent-cyan)]" />
              </div>
              <div className="bg-[var(--color-surface-2)] border border-[var(--color-border-subtle)] border-l-2 border-l-[var(--color-accent-cyan)] rounded-2xl rounded-tl-md px-5 py-4 flex items-center gap-1.5">
                <span className="w-2 h-2 bg-[var(--color-accent-cyan)] rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-2 h-2 bg-[var(--color-accent-cyan)] rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-2 h-2 bg-[var(--color-accent-cyan)] rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-[var(--color-border-subtle)]">
          <div className="relative flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea ref={textareaRef} value={input} onChange={e => { setInput(e.target.value); adjustTextarea(); }} onKeyDown={handleKeyDown}
                placeholder="Ask anything about your data..."
                rows={1}
                className="w-full bg-[var(--color-surface-2)] border border-[var(--color-border-subtle)] rounded-xl py-3 px-4 pr-16 text-base text-white placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent-cyan)] resize-none transition-all max-h-[120px]" />
              <div className="absolute right-3 bottom-2.5 flex items-center gap-2">
                <span className="text-xs text-[var(--color-text-muted)] font-mono">{input.length}/2000</span>
                <button onClick={() => handleSend()} disabled={!input.trim() || isTyping}
                  className="p-1.5 rounded-lg bg-[var(--color-accent-cyan)] text-black hover:bg-[var(--color-accent-cyan)]/80 disabled:opacity-30 disabled:cursor-not-allowed transition-all">
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
          <p className="text-xs text-[var(--color-text-muted)] text-center mt-2">AI can make mistakes. Verify critical data via primary reports.</p>
        </div>
      </div>
    </div>
  );
}

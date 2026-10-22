import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useKeyboardShortcut } from '../../hooks/useKeyboardShortcut';

interface Command {
  id: string;
  label: string;
  keywords: string[];
  action: () => void;
  category: string;
}

interface Props {
  onRunForecast?: (state?: string) => void;
  onRunPandemic?: () => void;
}

export default function CommandPalette({ onRunForecast, onRunPandemic }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  useKeyboardShortcut('k', () => setOpen(true), ['meta']);
  useKeyboardShortcut('k', () => setOpen(true), ['ctrl']);

  const commands: Command[] = [
    { id: 'cc', label: 'Command Center', keywords: ['dashboard', 'home', 'main'], category: 'Pages', action: () => navigate('/dashboard') },
    { id: 'map', label: 'District Intelligence', keywords: ['map', 'state', 'region'], category: 'Pages', action: () => navigate('/dashboard/map') },
    { id: 'rmap', label: 'Region Map', keywords: ['region', 'area', 'geography'], category: 'Pages', action: () => navigate('/dashboard/region-map') },
    { id: 'forecast', label: 'Bed Forecasting', keywords: ['bed', 'forecast', 'capacity', 'occupancy'], category: 'Pages', action: () => navigate('/dashboard/beds') },
    { id: 'mortality', label: 'Mortality Analytics', keywords: ['death', 'mortality', 'survival', 'fatality'], category: 'Pages', action: () => navigate('/dashboard/mortality') },
    { id: 'rankings', label: 'Hospital Rankings', keywords: ['rank', 'hospital', 'score', 'top'], category: 'Pages', action: () => navigate('/dashboard/hospitals') },
    { id: 'ai', label: 'AI Assistant', keywords: ['chat', 'ai', 'ask', 'question', 'help'], category: 'Pages', action: () => navigate('/dashboard/ai') },
    { id: 'pandemic', label: 'Pandemic Simulator', keywords: ['pandemic', 'outbreak', 'simulation', 'virus'], category: 'Pages', action: () => navigate('/dashboard/pandemic') },
    { id: 'patients', label: 'Patient Records', keywords: ['patient', 'people', 'records'], category: 'Pages', action: () => navigate('/dashboard/patients') },
    { id: 'run-forecast', label: 'Run Bed Forecast → Tamil Nadu', keywords: ['run', 'forecast', 'tamil nadu', 'simulate'], category: 'Actions', action: () => { setOpen(false); onRunForecast?.('Tamil Nadu'); navigate('/dashboard/beds'); } },
    { id: 'run-pandemic', label: 'Run Pandemic Simulation → COVID-19', keywords: ['run', 'pandemic', 'simulate', 'covid'], category: 'Actions', action: () => { setOpen(false); onRunPandemic?.(); navigate('/dashboard/pandemic'); } },
    { id: 'ask-ai', label: 'Ask AI: Compare hospitals for cardiac care', keywords: ['ask', 'ai', 'cardiac', 'hospital', 'compare'], category: 'Actions', action: () => { setOpen(false); navigate('/dashboard/ai'); } },
  ];

  const filtered = query.trim()
    ? commands.filter(c => c.keywords.some(k => k.includes(query.toLowerCase())) || c.label.toLowerCase().includes(query.toLowerCase()))
    : commands;

  useEffect(() => { setSelectedIndex(0); }, [query]);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
  }, [open]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') { setOpen(false); setQuery(''); }
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIndex(i => Math.min(i + 1, filtered.length - 1)); }
    if (e.key === 'ArrowUp') { e.preventDefault(); setSelectedIndex(i => Math.max(i - 1, 0)); }
    if (e.key === 'Enter' && filtered[selectedIndex]) {
      filtered[selectedIndex].action();
      setOpen(false);
      setQuery('');
    }
  }, [filtered, selectedIndex]);

  if (!open) return null;

  const categories = [...new Set(filtered.map(c => c.category))];

  return (
    <div
      className="fixed inset-0 z-[9998] flex items-start justify-center pt-[15vh]"
      style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)' }}
      onClick={() => { setOpen(false); setQuery(''); }}
    >
      <div
        className="w-full max-w-[560px] rounded-2xl border border-[var(--color-border-strong)] shadow-2xl overflow-hidden"
        style={{ background: 'rgba(11,17,32,0.95)', backdropFilter: 'blur(20px)' }}
        onClick={e => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--color-border-subtle)]">
          <svg className="w-4 h-4 text-[var(--color-text-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search pages, actions..."
            className="flex-1 bg-transparent text-sm text-[var(--color-text-primary)] outline-none placeholder-[var(--color-text-muted)]"
          />
          <span className="text-[10px] font-mono text-[var(--color-text-muted)] bg-[var(--color-surface-2)] px-1.5 py-0.5 rounded">ESC</span>
        </div>
        <div className="max-h-[360px] overflow-y-auto p-2">
          {categories.map(cat => (
            <div key={cat}>
              <p className="text-[10px] font-mono text-[var(--color-text-muted)] uppercase tracking-wider px-3 pt-3 pb-1">{cat}</p>
              {filtered.filter(c => c.category === cat).map((cmd, i) => {
                const actualIndex = filtered.indexOf(cmd);
                return (
                  <button
                    key={cmd.id}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-left transition-colors"
                    style={{
                      background: actualIndex === selectedIndex ? 'var(--color-surface-2)' : 'transparent',
                      color: actualIndex === selectedIndex ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                    }}
                    onMouseEnter={() => setSelectedIndex(actualIndex)}
                    onClick={() => { cmd.action(); setOpen(false); setQuery(''); }}
                  >
                    <span className="w-6 h-6 rounded-md flex items-center justify-center text-xs font-mono"
                      style={{ background: 'var(--color-surface-2)', color: 'var(--color-accent-cyan)' }}>
                      {cmd.category === 'Pages' ? '→' : '▶'}
                    </span>
                    <span className="flex-1">{cmd.label}</span>
                    {cmd.category === 'Pages' && (
                      <span className="text-[10px] font-mono text-[var(--color-text-muted)]">↵</span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
          {filtered.length === 0 && (
            <p className="text-sm text-[var(--color-text-muted)] text-center py-8">No results for "{query}"</p>
          )}
        </div>
        <div className="flex items-center gap-4 px-4 py-2 border-t border-[var(--color-border-subtle)] text-[10px] font-mono text-[var(--color-text-muted)]">
          <span>↑↓ Navigate</span>
          <span>↵ Select</span>
          <span>Esc Close</span>
        </div>
      </div>
    </div>
  );
}

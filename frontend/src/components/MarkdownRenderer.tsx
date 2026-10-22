import React from 'react';

const CODE_BLOCK = /```(\w*)\n([\s\S]*?)```/g;
const BOLD = /\*\*(.+?)\*\*/g;
const ITALIC = /(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g;
const INLINE_CODE = /`(.+?)`/g;
const BULLET = /^[\s]*[-*+]\s+(.*)$/m;
const NUMBERED = /^[\s]*\d+[.)]\s+(.*)$/m;
const NEWLINE = /\n/g;

interface MatchPart {
  idx: number;
  end: number;
  text: string;
  wrap: (s: string, i: number) => React.ReactNode;
}

function parseLine(line: string, key: string): React.ReactNode {
  const patterns: Array<{ re: RegExp; wrap: (s: string, i: number) => React.ReactNode }> = [
    { re: BOLD, wrap: (s, i) => <strong key={key + 'b' + i} className="font-semibold text-white">{s}</strong> },
    { re: ITALIC, wrap: (s, i) => <em key={key + 'i' + i} className="italic text-[var(--color-text-secondary)]">{s}</em> },
    { re: INLINE_CODE, wrap: (s, i) => <code key={key + 'c' + i} className="bg-[var(--color-bg-primary)] px-1.5 py-0.5 rounded text-xs font-mono text-cyan-300">{s}</code> },
  ];

  const matches: MatchPart[] = [];
  for (const p of patterns) {
    let m;
    p.re.lastIndex = 0;
    while ((m = p.re.exec(line)) !== null) {
      matches.push({ idx: m.index, end: m.index + m[0].length, text: m[1], wrap: p.wrap });
    }
  }
  matches.sort((a, b) => a.idx - b.idx);

  if (matches.length === 0) return line;

  let cursor = 0;
  const elements: React.ReactNode[] = [];
  for (const m of matches) {
    if (m.idx > cursor) {
      elements.push(<span key={key + 't' + cursor}>{line.slice(cursor, m.idx)}</span>);
    }
    elements.push(m.wrap(m.text, elements.length));
    cursor = m.end;
  }
  if (cursor < line.length) {
    elements.push(<span key={key + 'e' + cursor}>{line.slice(cursor)}</span>);
  }
  return elements.length === 1 ? elements[0] : <React.Fragment key={key}>{elements}</React.Fragment>;
}

export default function MarkdownRenderer({ text }: { text?: string }) {
  if (!text) return null;

  const blocks = text.split(/(```[\s\S]*?```)/g);
  const elements: React.ReactNode[] = [];

  blocks.forEach((block: string, bi: number) => {
    const codeMatch = block.match(CODE_BLOCK);
    if (codeMatch) {
      const match = Array.from(block.matchAll(CODE_BLOCK))[0];
      const lang = match[1];
      const code = match[2];
      elements.push(
        <pre key={bi} className="bg-[var(--color-bg-primary)] rounded-lg p-4 my-2 overflow-x-auto text-sm font-mono text-cyan-300 border border-[var(--color-border)]">
          <code>{code.trim()}</code>
        </pre>
      );
      return;
    }

    const lines = block.split(NEWLINE);
    let inList = false;
    let listItems: React.ReactNode[] = [];

    lines.forEach((line, li) => {
      const bulletMatch = line.match(BULLET);
      const numberedMatch = line.match(NUMBERED);
      const isHeader = line.startsWith('### ') || line.startsWith('## ') || line.startsWith('# ');

      if (bulletMatch || numberedMatch) {
        inList = true;
        const content = (bulletMatch || numberedMatch)![1];
        listItems.push(
          <li key={li} className="text-sm leading-relaxed text-[var(--color-text-primary)] mb-1">
            {parseLine(content, `${bi}-${li}`)}
          </li>
        );
        return;
      }

      if (inList) {
        elements.push(
          <ul key={`ul-${bi}-${li}`} className="list-disc list-inside space-y-1 my-2 pl-2">
            {listItems}
          </ul>
        );
        inList = false;
        listItems = [];
      }

      if (line.trim() === '') {
        elements.push(<div key={`sp-${bi}-${li}`} className="h-2" />);
        return;
      }

      if (isHeader) {
        const level = line.startsWith('### ') ? 3 : line.startsWith('## ') ? 2 : 1;
        const content = line.replace(/^#{1,3} /, '');
        const sizes = { 1: 'text-lg', 2: 'text-base', 3: 'text-sm' };
        const Tag = level === 1 ? 'h1' : level === 2 ? 'h2' : 'h3';
        elements.push(
          <Tag key={`h-${bi}-${li}`} className={`font-bold mt-3 mb-1 text-white ${sizes[level] || 'text-sm'}`}>
            {parseLine(content, `${bi}-h-${li}`)}
          </Tag>
        );
        return;
      }

      elements.push(
        <p key={`p-${bi}-${li}`} className="text-sm leading-relaxed text-[var(--color-text-primary)] mb-1">
          {parseLine(line, `${bi}-p-${li}`)}
        </p>
      );
    });

    if (inList) {
      elements.push(
        <ul key={`ul-end-${bi}`} className="list-disc list-inside space-y-1 my-2 pl-2">
          {listItems}
        </ul>
      );
    }
  });

  return <div className="space-y-0.5">{elements}</div>;
}


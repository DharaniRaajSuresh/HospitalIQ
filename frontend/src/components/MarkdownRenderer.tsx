// @ts-nocheck
import React from 'react';

const CODE_BLOCK = /```(\w*)\n([\s\S]*?)```/g;
const BOLD = /\*\*(.+?)\*\*/g;
const ITALIC = /(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g;
const INLINE_CODE = /`(.+?)`/g;
const BULLET = /^[\s]*[-*+]\s+(.*)$/gm;
const NUMBERED = /^[\s]*\d+[.)]\s+(.*)$/gm;
const NEWLINE = /\n/g;

function parseLine(line, key) {
  const parts = [];
  let remaining = line;
  let lastIdx = 0;

  const patterns = [
    { re: BOLD, wrap: (s) => <strong key={key + 'b' + parts.length} className="font-semibold text-white">{s}</strong> },
    { re: ITALIC, wrap: (s) => <em key={key + 'i' + parts.length} className="italic text-[var(--color-text-secondary)]">{s}</em> },
    { re: INLINE_CODE, wrap: (s) => <code key={key + 'c' + parts.length} className="bg-[var(--color-bg-primary)] px-1.5 py-0.5 rounded text-xs font-mono text-cyan-300">{s}</code> },
  ];

  const matches = [];
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
  const elements = [];
  for (const m of matches) {
    if (m.idx > cursor) {
      elements.push(<span key={key + 't' + cursor}>{line.slice(cursor, m.idx)}</span>);
    }
    elements.push(m.wrap(m.text));
    cursor = m.end;
  }
  if (cursor < line.length) {
    elements.push(<span key={key + 'e' + cursor}>{line.slice(cursor)}</span>);
  }
  return elements.length === 1 ? elements[0] : <React.Fragment key={key}>{elements}</React.Fragment>;
}

export default function MarkdownRenderer({ text }) {
  if (!text) return null;

  const blocks = text.split(/(```[\s\S]*?```)/g);
  const elements = [];

  blocks.forEach((block, bi) => {
    const codeMatch = block.match(CODE_BLOCK);
    if (codeMatch) {
      const [, lang, code] = Array.from(block.matchAll(CODE_BLOCK))[0];
      elements.push(
        <pre key={bi} className="bg-[var(--color-bg-primary)] rounded-lg p-4 my-2 overflow-x-auto text-sm font-mono text-cyan-300 border border-[var(--color-border)]">
          <code>{code.trim()}</code>
        </pre>
      );
      return;
    }

    const lines = block.split(NEWLINE);
    let inList = false;
    let listItems = [];

    lines.forEach((line, li) => {
      const bulletMatch = line.match(BULLET);
      const numberedMatch = line.match(NUMBERED);
      const isHeader = line.startsWith('### ') || line.startsWith('## ') || line.startsWith('# ');

      if (bulletMatch || numberedMatch) {
        inList = true;
        const content = bulletMatch ? bulletMatch[1] : numberedMatch[1];
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
        const H = `h${level}`;
        const sizes = { 1: 'text-lg', 2: 'text-base', 3: 'text-sm' };
        elements.push(
          <H key={`h-${bi}-${li}`} className={`font-bold mt-3 mb-1 text-white ${sizes[level] || 'text-sm'}`}>
            {parseLine(content, `${bi}-h-${li}`)}
          </H>
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


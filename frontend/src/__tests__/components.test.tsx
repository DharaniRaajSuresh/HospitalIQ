import { describe, it, expect, vi, beforeAll } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

vi.mock('framer-motion', () => ({
  useInView: () => true,
  motion: new Proxy({}, { get: () => 'div' }),
  AnimatePresence: ({ children }) => children,
  useMotionValue: (v) => ({ get: () => v }),
  useTransform: (v) => v,
  useSpring: (v) => v,
}));

beforeAll(() => {
  global.IntersectionObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

describe('Button component', () => {
  it('renders with text', async () => {
    const mod = await import('../components/ui/Button');
    const Button = mod.default;
    render(React.createElement(Button, null, 'Click'));
    expect(screen.getByText('Click')).toBeDefined();
  });
});

describe('Badge component', () => {
  it('renders status text', async () => {
    const mod = await import('../components/ui/Badge');
    const Badge = mod.default;
    render(React.createElement(Badge, null, 'Active'));
    expect(screen.getByText('Active')).toBeDefined();
  });
});

describe('GlassCard component', () => {
  it('renders children', async () => {
    const mod = await import('../components/ui/GlassCard');
    const GlassCard = mod.default;
    render(React.createElement(GlassCard, null,
      React.createElement('p', null, 'Card content')));
    expect(screen.getByText('Card content')).toBeDefined();
  });
});

describe('KPICard component', () => {
  it('renders label, formatted value, and trend', async () => {
    const mod = await import('../components/ui/KPICard');
    const KPICard = mod.default;
    render(React.createElement(KPICard, { label: 'Beds', value: 1200, trend: 5 }));
    expect(screen.getByText('Beds')).toBeDefined();
    expect(screen.getByText('1,200')).toBeDefined();
    expect(screen.getByText('+5%')).toBeDefined();
  });

  it('renders with string trend', async () => {
    const mod = await import('../components/ui/KPICard');
    const KPICard = mod.default;
    render(React.createElement(KPICard, { label: 'Status', value: 85, trend: 'stable' }));
    expect(screen.getByText('Status')).toBeDefined();
    expect(screen.getByText('85')).toBeDefined();
    expect(screen.getByText('stable')).toBeDefined();
  });

  it('displays dash for null value', async () => {
    const mod = await import('../components/ui/KPICard');
    const KPICard = mod.default;
    render(React.createElement(KPICard, { label: 'Empty', value: null }));
    expect(screen.getByText('—')).toBeDefined();
  });
});

describe('AnimatedCounter component', () => {
  it('renders formatted number', async () => {
    const mod = await import('../components/ui/AnimatedCounter');
    const AnimatedCounter = mod.default;
    const { container } = render(React.createElement(AnimatedCounter, { value: 1000 }));
    expect(container.textContent).toBe('0');
  });
});

describe('PageTransition component', () => {
  it('renders children', async () => {
    const mod = await import('../components/ui/PageTransition');
    const PageTransition = mod.default;
    render(React.createElement(PageTransition, null,
      React.createElement('h1', null, 'Page')));
    expect(screen.getByText('Page')).toBeDefined();
  });
});

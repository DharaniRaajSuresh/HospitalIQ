import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

vi.mock('../pages/LandingPage', () => ({ default: () => <div data-testid="landing-page">Landing</div> }));
vi.mock('../pages/CommandCenter', () => ({ default: () => <div data-testid="command-center">Command</div> }));
vi.mock('../pages/ForecastingCenter', () => ({ default: () => <div data-testid="bed-forecast">Forecast</div> }));
vi.mock('../pages/MortalityAnalytics', () => ({ default: () => <div data-testid="mortality">Mortality</div> }));
vi.mock('../pages/HospitalRankingsPage', () => ({ default: () => <div data-testid="rankings">Rankings</div> }));
vi.mock('../pages/IntelligenceMap', () => ({ default: () => <div data-testid="intel-map">Map</div> }));
vi.mock('../pages/RegionalMap', () => ({ default: () => <div data-testid="regional-map">Regional</div> }));
vi.mock('../pages/AnalyticsDashboard', () => ({ default: () => <div data-testid="analytics">Analytics</div> }));
vi.mock('../pages/AICopilot', () => ({ default: () => <div data-testid="ai-copilot">AI</div> }));
vi.mock('../pages/PandemicScenario', () => ({ default: () => <div data-testid="pandemic">Pandemic</div> }));
vi.mock('../layouts/DashboardLayout', () => ({ default: () => <div data-testid="dashboard-layout">Layout</div> }));
vi.mock('../components/FloatingCopilot', () => ({ default: () => <div data-testid="floating-copilot">Copilot</div> }));

describe('App routing', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/');
  });

  it('renders landing page at /', async () => {
    render((await import('../App')).default());
    await waitFor(() => expect(screen.getByTestId('landing-page')).toBeDefined());
  });

  it('renders floating copilot on every page', async () => {
    render((await import('../App')).default());
    await waitFor(() => expect(screen.getByTestId('floating-copilot')).toBeDefined());
  });
});

describe('api.js module', () => {
  let api;

  beforeEach(async () => {
    api = await import('../api');
  });

  it('exports all required API functions', () => {
    const funcs = ['login', 'register', 'logout', 'getMe', 'isAuthenticated',
                   'getStats', 'getStates', 'getDistricts', 'getBedForecast',
                   'predictMortality', 'getHospitalRankings', 'getLocationStats',
                   'getDistrictList', 'getLocalities', 'getAdmissions'];
    funcs.forEach(f => {
      expect(typeof api[f]).toBe('function');
    });
  });
});

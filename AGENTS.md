# Project Context

## Backend: FastAPI + SQLite + ML

### ML Models (loaded at startup in `main.py`)
| Model | Algorithm | Status | Notes |
|---|---|---|---|
| **BedPredictor** | GradientBoostingRegressor | **R² ~0.64** | Predicts bed availability per state/ward |
| **MortalityPredictor** | XGBoost | **R² ~0.85** | Predicts death rates per district/age/cause |
| **ForecastPredictor** | XGBoost (was Ridge) | **MAPE 9.8% cases, 13.8% deaths** | Switched from Ridge in June 2026 |
| **HospitalPredictor** | RandomForest | — | Capacity/resource ranking |
| **PatientRiskPredictor** | 3-model ensemble (RF + GB + XGB) | — | Patient-level risk scoring |
| **ScenarioPredictor** | XGBoost | **Train MAPE 5.7%, Test 28.7% (cases); Train 19.4%, Test 71.8% (deaths)** | Upgraded from Ridge (MAPE 414%/615%) in June 2026 |
| **RiskPredictor** | None (deterministic formula) | — | Replaced fake RandomForest (R² 0.99 was artifact) |

## Verification Status (June 2026)

### Tests: ALL 58 PASS
- `python -m pytest tests/ -v` → 58/58 passed, 40 warnings
- ML models load & predict correctly

### Frontend Build: SUCCESS
- `npm run build` → 32 chunks, 0 errors
- Vite 8 compat: manualChunks switched from object to function syntax

### Frontend-Backend Integration: ALL PAGES FIXED
7 pages were using raw `fetch()` instead of `api.js` functions, causing 401 errors:
- `ForecastingCenter.jsx` → `fetchForecast()` (uses `api.js`)
- `AssistantChatbot.jsx` → `chatAI()`, `getSuggestions()` (uses `api.js`)
- `RegionalMap.jsx` → `fetchMapData()` (uses `api.js`)
- `MortalityAnalytics.jsx` → `fetchMortalityData()` (uses `api.js`)
- `PatientDetail.jsx` → `fetchPatientDetails()`, `fetchPatientRisk()` (uses `api.js`)
- `PatientRecords.jsx` → raw fetch replaced
- `PandemicScenario.jsx` → raw fetch replaced

### api.js Exports Now Include:
- `authFetch` (wraps fetch with credentials & Authorization header)
- `chatAI`, `getSuggestions` (AI endpoints)
- All other CRUD wrappers

### Dead Files Removed (10 files):
**Frontend components (8):** StatsOverview, MortalityPredictor, IndiaMap, HospitalRankings, BedForecast, Analytics, PremiumChart, AuroraBackground
**Backend (2):** redis_cache.py, base_service.py + core/__init__.py export fix
**ML scripts (1):** train_annual_scenario.py

### ML Pipeline Refactoring
- **prediction_log bug:** `model_version=status` was logging "ml_model"/"db_trend" as version → fixed to `f"{module}_v1"`
- **mortality risk labels:** Were using K-Means cluster labels (0,1,2) → switched to death rate thresholds (Critical/High/Moderate/Low)
- **forecast model:** Ridge (high bias) → XGBoost with tuned params
- **mortality model:** RandomForest (no regularization) → XGBoost with proper chronological train/test split
- **risk model:** RandomForest (R² 0.99 due to data leakage from formula-like features) → direct deterministic formula
- **patient_risk training:** Created reproducible script with 3-model ensemble
- **scenario training:** Created reproducible pipeline from historical data

## ML vs Hardcoded Audit

| Endpoint | ML Used? | Fallback | Verdict |
|---|---|---|---|
| `POST /predict/beds` | ✅ GBR model | db_trend (DB linear) → **estimated (HARDCODED `450+i*8`)** | ⚠️ last resort hardcoded, unreachable in practice |
| `POST /predict/mortality` | ✅ XGBoost | db_grounded (DB avg death rates) | ✅ |
| `GET /pandemic/scenario` | ✅ 6 ML models | DB-driven for all components | ✅ |
| `GET /patients/{id}/risk` | ✅ 3-model ensemble | Error if not loaded | ✅ |
| `GET /hospitals/rankings` | N/A (pure DB query) | — | ✅ |
| `GET /hospitals/distribution` | N/A (pure DB query) | — | ✅ |
| `GET /stats` | N/A (pure DB query) | — | ✅ |
| `GET /locations/*` | N/A (pure DB queries) | — | ✅ |
| `POST /ai/chat` | ✅ LLM-based | — | ✅ |
| `GET /ai/suggestions` | ✅ LLM-based | — | ✅ |
| `GET /health/*` | N/A (status checks) | — | ✅ |

**Remaining issue:** `/predict/beds` lines 64-72 hardcodes `450+i*8` beds, `300-i*5` available, `0.65+i*0.02` occupancy as last resort. Unreachable because ML model loads + DB has data, but technically present.

---

## Frontend Overhaul (June 2026)

### Goal
Transform all 5 priority pages into senior-level product for mentor live demo — consistent dark theme with cyan/violet accents, surface layers, animations respecting `prefers-reduced-motion`, fully typed (no `@ts-nocheck` in new code).

### Architecture — All Done
| File | Purpose |
|---|---|
| `src/hooks/useApi.ts` | Universal data-fetching hook with retry, idle/loading/success/error states, auto-refetch |
| `src/hooks/useDebounce.ts` | Generic debounce hook |
| `src/hooks/useKeyboardShortcut.ts` | Keyboard shortcut hook with ctrl/meta/shift/alt modifiers |
| `src/types/api.ts` | Full TypeScript interfaces for all backend API responses |
| `src/components/ui/ErrorBoundary.tsx` | Class-based with custom fallback + Try Again |
| `src/context/ToastContext.tsx` | Toast notifications (success/error/warning/info), slide-in, 4s auto-dismiss |
| `src/context/LoadingBarContext.tsx` | Global 2px cyan/violet progress bar |
| `src/components/ui/SkeletonLoader.tsx` | Variant-based skeleton with diagonal shimmer |
| `src/components/ui/StatusBadge.tsx` | ML fallback tier badge (ml_model/db_trend/estimated/live/cached) |
| `src/components/ui/MetricCard.tsx` | Animated stat card with requestAnimationFrame counter + SVG sparkline |
| `src/components/ui/PipelineVisualizer.tsx` | Animated 6-step ML pipeline with pending/running/done states |
| `src/components/ui/CommandPalette.tsx` | ⌘K command palette with keyboard nav, grouped commands |
| `src/components/ui/PageTransition.tsx` | Route entrance animation (fade + slide-up) |

### Page Overhauls — All 5 Done
| Page | Key Features |
|---|---|
| **CommandCenter** | 3-column mission control: IST clock, 6 MetricCards with sparklines, system health indicators with 30s `/health/ready` polling, intelligence feed with severity-coded alerts, Recharts area chart for state-wise bed distribution, quick-action cards |
| **ForecastingCenter** | 2-column: 340px control panel with searchable grouped state dropdown, 4-button ward toggle, custom slider (3/6/12/24 months), pandemic surge toggle; charts with ComposedChart, scenario comparison chips, model metadata panel with R²/StatusBadge, collapsible data table, CSV export |
| **PandemicScenario** | Disease card selector (6 diseases with CFR/R₀), state + year params, 6-step PipelineVisualizer loading, risk gauge SVG donut with fill animation, timeline BarChart with TODAY reference line, intelligence briefing with priority-coded recommendations, expandable hospitals-at-risk list |
| **AssistantChatbot** | 2-pane: 280px session history (Today/This Week/Earlier) + conversation; separate sessions with create/delete; quick topic tags; suggested queries; redesigned bubbles (AI: cyan left-border, copy/thumbs buttons); staggered typing indicator; multi-line textarea with char counter |
| **PatientRecords** | Debounced search (300ms), multi-select filter chips (Blood/Gender/Risk), card/table view toggle persisted to sessionStorage, initials avatar with color derived from ID, sortable table, pagination |
| **PatientDetail** | 3-panel: identity (80px avatar, demographics, pre-existing), risk assessment with semicircle SVG gauge + feature bars grouped by category + PipelineVisualizer, history timeline (vaccines/travel/family with icon bullets) |

### Global UX — Done
- Loading bar context integrated in App.tsx
- Route-based `document.title` on all major pages
- PageTransition already existed with fade+slide animation
- Empty states on all overhauled pages

### TypeScript Cleanup
All 12 files with `@ts-nocheck` have been fixed. `tsc --noEmit` passes with 0 errors:
- Fixed types for `Particle` class in `FloatingParticles.tsx`
- Fixed dynamic JSX tags in `MarkdownRenderer.tsx`  
- Fixed Leaflet property access in `MapView.tsx`
- Fixed `Promise.all` type inference in `LocationDetail.tsx`
- Fixed `AnimatedCounter` formatter prop in `KPICard.tsx`
- Fixed `PageTransition` locationKey prop in `DashboardLayout.tsx`
- Added `Window.__auth_token` declaration in `vite-env.d.ts`
- Fixed numerous `unknown` type issues across all 6 pages

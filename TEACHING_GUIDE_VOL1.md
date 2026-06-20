# HOSPi — Complete Reverse-Engineered Teaching Guide

## Volume 1: Project Map & Architecture Overview

> **Purpose:** This is your internal engineering handbook. Every file, every API, every model, every deployment detail in this project, fully explained with production-grade depth. Study this document for 2-3 weeks and you will be able to discuss every aspect of this project at FAANG-level interviews.

---

## 1. WHAT IS THIS PROJECT?

### Layer 1 — Beginner Explanation

HospitalIQ (called "HOSPi" internally) is a **healthcare intelligence web application** for India. It helps hospital administrators, public health officials, and policymakers:

1. **Predict future hospital bed demand** — "How many ICU beds will Tamil Nadu need in 2030?"
2. **Forecast disease mortality** — "What will the death rate for cardiac disease be in Chennai in 2026?"
3. **Simulate pandemic scenarios** — "What happens if a Nipah outbreak hits Kerala?"
4. **Rank hospitals by performance** — "Which hospitals have the best success rate for cardiac surgery?"
5. **Assess patient risk** — "Given this patient's age, pre-existing conditions, and vaccine history, what is their risk if they contract COVID-19?"
6. **Chat with an AI assistant** — "Compare government vs private hospitals for diabetes treatment."

The project has **three main parts**:
- **Frontend** (React + TypeScript) — the visual dashboard you see in the browser
- **Backend** (Python FastAPI) — the server that processes requests and runs ML models
- **ML Pipeline** (Python) — the training scripts that create the ML models

### Layer 2 — Technical Explanation

HospitalIQ is a **full-stack data-intensive web application** with the following technical characteristics:

- **Database:** 16 SQLAlchemy ORM tables in SQLite (with automatic PostgreSQL fallback), containing ~1.64M records total
- **ML Models:** 6 trained models (GradientBoostingRegressor, XGBoost, RandomForest) + 1 deterministic formula + 1 ensemble (3-model)
- **API Surface:** 11 router modules exposing 30+ REST endpoints under `/api/v1/`
- **Frontend:** React 19, Vite 8, TypeScript 6, Tailwind 4, 12 lazy-loaded page components, 32 production chunks
- **Auth:** JWT with httpOnly cookies + Bearer header fallback, bcrypt(12 rounds)
- **Infrastructure:** Docker Compose (3 services), nginx reverse proxy, OpenTelemetry tracing, Prometheus metrics, rate limiting (slowapi)

### Layer 3 — Production / Industry Explanation

HospitalIQ is a **resume-grade full-stack ML platform** architected with:

- **Repository Pattern** — Data access abstracted into `repositories/` (BedRepository, PatientRepository, etc.) enabling testable, swapable data layers
- **Abstract Base Classes** — `BasePredictor` provides template method pattern for all 6 ML predictors, enforcing consistent `load_model()`, `predict()`, `validate_input()`, `get_feature_names()` contracts
- **Automatic Fallback Architecture** — Every ML prediction endpoint has 3 tiers: ML model → DB-driven trend → hardcoded estimate. If the model fails to load, the system degrades gracefully rather than crashing
- **In-Memory TTL Cache** — Heavy aggregation queries (location stats, district lists) cached with 5-minute TTL to prevent SQLite from being hammered by 30+ parallel React component requests
- **MVC-like Layering** — Routes (`routers/`) are thin; business logic lives in `services/` and `predictors/`; data access in `repositories/`; ML training in separate standalone scripts under `ml_pipeline/`

---

## 2. SYSTEM ARCHITECTURE — COMPLETE DEPENDENCY GRAPH

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React 19 + Vite 8)                │
│                                                                     │
│  main.tsx → App.tsx ← BrowserRouter                                │
│               ├── LandingPage.tsx  (/)                             │
│               └── DashboardLayout.tsx  (/dashboard/*)              │
│                     ├── CommandCenter.tsx                          │
│                     ├── ForecastingCenter.tsx  ← api.getBedForecast│
│                     ├── MortalityAnalytics.tsx  ← api.predictMort  │
│                     ├── HospitalRankingsPage.tsx  ← api.getRankings│
│                     ├── IntelligenceMap.tsx                        │
│                     ├── RegionalMap.tsx                            │
│                     ├── AnalyticsDashboard.tsx                     │
│                     ├── PandemicScenario.tsx  ← api.getScenario    │
│                     ├── PatientRecords.tsx  ← api.getPatients      │
│                     ├── PatientDetail.tsx  ← api.getPatientRisk    │
│                     └── AssistantChatbot.tsx  ← api.chatAI         │
│                                                                     │
│  ALL pages call → api.ts ← authFetch (Bearer + cookie)             │
│                     ├── login/register/logout/getMe                │
│                     ├── getStats/getStates/getDistricts            │
│                     ├── getBedForecast/predictMortality            │
│                     ├── getPandemicScenario/getPatientRisk         │
│                     ├── getHospitalRankings/getHospitalDistribution│
│                     ├── chatAI/getSuggestions                      │
│                     └── getLocationStats/getDistrictList/...       │
│                                                                     │
│  HTTP → nginx (port 3000) → /api/ proxy_pass → backend:8000       │
└──────────────────────┬──────────────────────────────────────────────┘
                       │ HTTP REST (JSON)
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI + Python 3.12)                 │
│                                                                     │
│  main.py (app startup, CORS, tracing, lifespan)                    │
│    ├── lifespan() → init_db(), load ML predictors, refresh_scheduler│
│    ├── CORSMiddleware (allow frontend origins)                      │
│    ├── slowapi RateLimiter (1000 req/h default)                     │
│    ├── OpenTelemetry tracing setup                                  │
│    └── 9 router includes (health, predictions, stats, locations,    │
│         pandemic, patients, ai, auth, map)                          │
│                                                                     │
│  DATABASE LAYER:                                                     │
│  database.py → SQLAlchemy engine (PostgreSQL → SQLite auto-fallback)│
│                   ├── WAL mode, 64MB cache, mmap I/O for SQLite     │
│                   ├── SessionLocal (session factory)                │
│                   └── get_db() → FastAPI dependency injection       │
│                                                                     │
│  MODELS (models/__init__.py → 16 SQLAlchemy ORM classes):           │
│  ├── User (auth)                                                    │
│  ├── HospitalBed (beds time-series)                                 │
│  ├── MortalityRecord (death rates)                                  │
│  ├── HospitalOutcome (hospital performance)                         │
│  ├── Patient (demographics)                                         │
│  ├── PatientAdmission (admission records)                           │
│  ├── PandemicOutbreak (pandemic time-series)                        │
│  ├── PredictionLog (audit trail)                                    │
│  ├── StateSummary / DistrictSummary (pre-computed aggregates)       │
│  ├── ChatHistory (AI conversation)                                  │
│  ├── VirusRegistry (virus registry for patient risk)                │
│  └── VaccineHistory, TravelHistory, FamilyHistory (patient data)    │
│                                                                     │
│  PREDICTORS + INFERENCE:                                            │
│  core/base_predictor.py ← abstract base (template method pattern)  │
│    ├── load_model() → joblib load from ml_pipeline/data/models/    │
│    ├── predict() → @abstractmethod (each predictor implements)      │
│    ├── validate_input() → @abstractmethod                           │
│    └── get_feature_names() → @abstractmethod                        │
│                                                                     │
│  predictors/ (concrete implementations):                            │
│    ├── bed_predictor.py → GradientBoostingRegressor (11 features)   │
│    ├── mortality_predictor.py → XGBoost + KMeans (14 features)     │
│    ├── forecast_predictor.py → XGBoost (16 features, 2 models)     │
│    ├── hospital_predictor.py → RandomForest (8 features)            │
│    ├── scenario_predictor.py → XGBoost (7 features, 2 models)      │
│    ├── patient_risk_predictor.py → ensemble of 3 models             │
│    └── risk_predictor.py → deterministic formula (no model)         │
│                                                                     │
│  ROUTERS (thin controllers → delegate to services/predictors):     │
│    routers/predictions.py → POST /predict/beds, /predict/mortality  │
│    routers/patients.py → GET /patients/{id}/risk                    │
│    routers/pandemic.py → GET /pandemic/scenario                    │
│    routers/locations.py → GET /hospitals/rankings, /locations/*    │
│    routers/ai.py → POST /ai/chat, GET /ai/suggestions              │
│    routers/auth.py → POST /auth/login/register, GET /auth/me      │
│    routers/health.py → GET /health, /health/live, /health/ready    │
│    routers/stats.py → GET /stats (with 5-min TTL cache)            │
│    routers/map.py → GET /map/geojson                               │
│                                                                     │
│  SERVICES (business logic):                                         │
│    services/pandemic_service.py → 12 functions, 385 lines           │
│    services/summary_refresh.py → pre-computes StateSummary/District │
│                                                                     │
│  AI MODULE:                                                         │
│    ai/ai_assistant.py → HospitalAIAssistant class                   │
│    ai/gemini_client.py → Google Gemini API wrapper                  │
│    ai/context_fetcher.py → DB context for RAG                       │
│    ai/prompt_builder.py → constructs prompts with system context    │
│    ai/project_context.py → project/system description               │
└──────────────────────┬──────────────────────────────────────────────┘
                       │ Python API calls + joblib model loading
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│              ML PIPELINE (Standalone training scripts)              │
│                                                                     │
│  ml_pipeline/                                                       │
│    ├── module1_beds/train_model.py → GradientBoostingRegressor     │
│    ├── module2_mortality/train_model.py → XGBoost + KMeans         │
│    ├── module3_hospitals/train_model.py → RandomForest             │
│    ├── train_forecast.py → XGBoost (cases + deaths, 2 models)     │
│    ├── train_scenario.py → XGBoost (annual aggregates)             │
│    ├── train_patient_risk.py → 3-model ensemble (RF+GB+XGB)       │
│    ├── train_risk.py → metadata only (formula, no model)          │
│    ├── auto_retrain.py → production auto-retrain pipeline           │
│    ├── ml_utils.py → CV, MLflow tracking, model versioning         │
│    └── real_data_ingest.py → downloads COVID19-India API data      │
│                                                                     │
│  Output: ml_pipeline/data/models/*.pkl                              │
│    └── loaded by backend predictors at startup                      │
└──────────────────────┬──────────────────────────────────────────────┘
                       │ sqlalchemy
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 DATABASE (SQLite  or  PostgreSQL 16)                │
│                                                                     │
│  16 tables: User, HospitalBed, MortalityRecord, HospitalOutcome,    │
│  PandemicOutbreak, Patient, PatientAdmission, PredictionLog,        │
│  ChatHistory, VirusRegistry, VaccineHistory, TravelHistory,         │
│  FamilyHistory, StateSummary, DistrictSummary, Section             │
│                                                                     │
│  ~1.64M total records (all synthetic, based on real published data) │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. COMPLETE REQUEST TRACE

Let's trace a single request end-to-end. A user on the Forecasting Center page selects "Tamil Nadu", "ICU", 12 months ahead, and clicks "Run AI Simulation".

### Step 1 — Frontend: User clicks button

**File:** `frontend/src/pages/ForecastingCenter.tsx`, lines ~155-160

```typescript
const handleRunSimulation = useCallback(async (overrideMonths, overrideYear) => {
    setLoading(true);
    setError(null);
    const result = await getBedForecast({ state, ward_type: wardType, months_ahead: months, year: yr });
```

**What happens:** React calls `getBedForecast()` from `api.ts`, passing the form state (state= "Tamil Nadu", ward_type="ICU", months_ahead=12, year=2026).

### Step 2 — Frontend: API client builds request

**File:** `frontend/src/api.ts`, lines ~125-131

```typescript
export async function getBedForecast<T = unknown>({ state, ward_type, months_ahead, year }: BedForecastParams): Promise<T> {
  const params: Record<string, string> = { state, ward_type, months_ahead: String(months_ahead) };
  if (year) params.year = String(year);
  const qs = new URLSearchParams(params).toString();
  return authFetch<T>(`/predict/beds?${qs}`, { method: 'POST' });
}
```

**What happens:** `getBedForecast` constructs the query string `state=Tamil+Nadu&ward_type=ICU&months_ahead=12&year=2026`, then calls `authFetch()` with `{ method: 'POST' }`.

### Step 3 — Frontend: authFetch adds auth and sends

**File:** `frontend/src/api.ts`, lines ~50-80

```typescript
export async function authFetch<T = unknown>(path: string, options: AuthFetchOptions = {}): Promise<T> {
  const headers: Record<string, string> = { ...options.headers };
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  const token = getToken();  // reads window.__auth_token
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  // ... checks cache for GET requests (skipped: this is POST)
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers, credentials: 'include' });
```

**What happens:** 
- `authFetch` reads the JWT token from `window.__auth_token` (set during login)
- Adds `Authorization: Bearer <token>` header
- Adds `Content-Type: application/json`
- Calls `fetch('/api/v1/predict/beds?state=Tamil+Nadu&ward_type=ICU&months_ahead=12&year=2026', { method: 'POST', ... })`
- If the response is 401, dispatches a custom `auth:logout` event
- If the response is not OK, throws an error with status code
- If the response is OK, parses JSON and returns

### Step 4 — Network: nginx proxies to backend

**File:** `frontend/nginx.conf`

```
location /api/ {
    proxy_pass http://api:8000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

**What happens:** In production (Docker), nginx receives the request on port 3000, matches `/api/`, and forwards to the backend container at `http://api:8000/api/v1/predict/beds?...`. In development (Vite dev server), the `vite.config.js` proxy does the same.

### Step 5 — Backend: FastAPI routing

**File:** `backend/routers/predictions.py`, lines 27-54

```python
@router.post("/beds")
async def predict_beds(state: str, ward_type: str, months_ahead: int = 3, year: int = Query(None), db=Depends(get_db), user=Depends(require_user)):
```

**What happens:** FastAPI receives the POST request, matches `/api/v1/predict/beds`, extracts query parameters. Dependency injection:
1. `db=Depends(get_db)` — creates a new SQLAlchemy session from `SessionLocal`, wrapped in `try/finally`
2. `user=Depends(require_user)` — calls `get_current_user()` which extracts the JWT, decodes it, queries the `User` table, and returns the user. If no valid token, raises 401

### Step 6 — Backend: Business logic

```python
    # Try DB data first (for fallback trend computation)
    db_data = db.query(...).filter(...).all()

    # Try ML model
    try:
        if "bed" in loaded_predictors:
            predictor = loaded_predictors["bed"]
            result = predictor.predict({"state": state, "ward_type": ward_type,
                                        "months_ahead": months_ahead,
                                        "start_year": start_year, "start_month": start_month})
```

**What happens:**
- First, the endpoint queries the database for historical bed data for Tamil Nadu/ICU
- Then checks if the BedPredictor is loaded in `loaded_predictors` (a global dict populated at startup)
- Calls `predictor.predict()` with the params
- If ML model succeeds, returns ML forecast
- If ML model fails, falls back to DB-driven trend
- If DB also fails, raises 503

### Step 7 — ML Predictor

**File:** `backend/predictors/bed_predictor.py`, lines 130-192

```python
def predict(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    if not self.validate_input(input_data):  # validates state, ward_type, months_ahead
        raise ValueError(...)
    if not self._is_loaded:
        self.load_model()

    # Build 11 features for each month
    for i in range(input_data["months_ahead"]):
        features = [[
            math.sin(2 * math.pi * month / 12),  # month_sin
            math.cos(2 * math.pi * month / 12),  # month_cos
            (year - self._year_min) / self._year_range,  # year_normalized
            season, state_enc, ward_enc,
            lag_1, lag_3, lag_6, roll_3, roll_6,
        ]]
        prediction = float(self._model.predict(features)[0])
        prediction = prediction * growth_factor  # 2.5% annual growth post-2024
        history.append(prediction)
```

**What happens:**
- Validates that Tamil Nadu is a known state, ICU is a known ward type, 12 is within 1-120
- Loads the `bed_model.pkl` if not loaded
- For each of the 12 months:
  - Computes cyclical month features (sin/cos — allows the model to learn seasonality)
  - Computes year_normalized (2015→0, 2024→~0.82, etc.)
  - Gets lag features from the last known values
  - Calls `model.predict(features)` on the GradientBoostingRegressor
  - Applies a 2.5% annual growth factor for years beyond training data
  - Adds confidence bounds that widen with horizon (8% + 1.5% per month)
  - Feeds the prediction back as lag for the next month (iterative forecasting)

### Step 8 — Response flow back

The predictor returns `{"state": "Tamil Nadu", "ward_type": "ICU", "forecast": [...12 months...], ...}`. This is wrapped by the endpoint into `{"state": ..., "ward_type": ..., "forecast": ..., "status": "ml_model"}`. FastAPI serializes this to JSON. The response goes back through nginx to the browser.

### Step 9 — Frontend: API response processing

```typescript
const result = await getBedForecast({ state, ward_type: wardType, months_ahead: months, year: yr });
let forecast = result.forecast || [];
const mapped = forecast.map((f, i) => ({
    month: f.year ? `${(f.month_name || '').slice(0,3)} ${f.year}` : f.month_name,
    predicted: Math.round(f.predicted_beds * surgeFactor),
    lower: Math.round(f.predicted_beds * 0.8),
    upper: Math.round(f.predicted_beds * 1.2),
}));
setRawForecast(mapped);
```

**What happens:** The raw forecast data is mapped into chart-ready format and stored in React state. React re-renders the `ComposedChart` with the new data, showing the projected bed demand as a dashed line with confidence intervals.

---

## 4. FILE-BY-FILE: WHAT EVERY FILE DOES

### Root Directory Files

| File | Purpose | Why It Exists |
|---|---|---|
| `docker-compose.yml` | Orchestrates 3 Docker services (api, frontend, db) | Single command to run entire stack |
| `Dockerfile` | Builds backend container (Python 3.12-slim) | Docker image for the API server |
| `requirements.txt` | Points to `requirements.backend.txt` | Convention: root requirements file |
| `requirements.backend.txt` | All Python dependencies (FastAPI, SQLAlchemy, scikit-learn, XGBoost, etc.) | Pinned versions for reproducible builds |
| `pyproject.toml` | Project metadata + dev dependencies (pytest, black, ruff) | Modern Python packaging |
| `.gitignore` | Excludes pkl, db, node_modules, __pycache__, mlruns, dist | Standard repo hygiene |
| `render.yaml` | Render.com deployment config | PaaS deployment (alternative to Docker) |
| `README.md` | Full project documentation | External-facing docs |
| `AGENTS.md` | Internal audit trail & decision log | For AI agents & developer continuity |
| `.env` | Environment variables (DB URL, JWT secret, Gemini key) | Configuration (gitignored) |
| `seed_beds.py` | Standalone script to seed hospital bed data (35K records) | Data generation for demo |
| `seed_pandemic.py` | Standalone script to seed pandemic time-series (COVID-19 + other diseases) | Pandemic scenario data |
| `seed_patients.py` | Standalone script to seed patient records (40K records) | Patient demo data |
| `seed_patient_records.py` | Standalone script: 10K patients + vaccines + travel + family history | Patient risk demo data |
| `seed_scale_all.py` | Standalone script to scale all tables to 100K+ records | Stress/performance testing |
| `train_patient_risk.py` | Trains the 3-model patient risk ensemble | Reproducible model training |
| `run_pipeline.py` | Orchestrates full data pipeline (seed + train ML models) | One-command pipeline execution |
| `hospitaliq.db` | SQLite database (all demo data) | Local development database |
| `test_hospitaliq.db` | Test database (pytest fixtures) | Isolated test database |
| `start_frontend.py` | Helper script to start the frontend | Convenience for developers |

### Backend Core Files

| File | Lines | Purpose | Key Pattern |
|---|---|---|---|
| `backend/main.py` | 100 | Application entry point; lifespan, middleware, router registration | FastAPI lifespan context manager |
| `backend/config.py` | 82 | Settings class loaded from .env (Pydantic BaseSettings) | Singleton pattern via module-level instance |
| `backend/database.py` | 82 | SQLAlchemy engine with PostgreSQL→SQLite auto-fallback | Automatic degradation |
| `backend/auth.py` | 105 | JWT creation/verification, bcrypt hashing, cookie management | Dual auth: cookie + Bearer |
| `backend/app_state.py` | 11 | Global dict for loaded predictors + state name normalization | Shared mutable state (singleton) |
| `backend/models/__init__.py` | ~300 | All 16 SQLAlchemy ORM table definitions | Declarative base pattern |

### Backend Predictors

| Predictor | File | ML Model | Features | Metrics |
|---|---|---|---|---|
| Bed | `bed_predictor.py` | GradientBoostingRegressor | 11 (sin/cos month, lag, rolling avg) | R² ~0.64 |
| Mortality | `mortality_predictor.py` | XGBoost + KMeans clustering | 14 (month sin/cos, lag, encoding) | R² ~0.85 |
| Forecast | `forecast_predictor.py` | XGBoost (2 models: cases + deaths) | 16 (lag cases, lag deaths, disease params) | MAPE 9.8% cases, 13.8% deaths |
| Hospital | `hospital_predictor.py` | RandomForest | 8 (beds, specialists, accreditation) | — |
| Scenario | `scenario_predictor.py` | XGBoost (2 models: annual cases + deaths) | 7 (year, cfr, r0, state) | Train MAPE 5.7%, Test 28.7% |
| PatientRisk | `patient_risk_predictor.py` | 3-model ensemble (RF + GB + XGB) | 15 features | — |
| Risk | `risk_predictor.py` | Deterministic formula (no model) | 12 features (log-based scoring) | N/A (formula) |

### Backend Router Responsibilities

| Router | Endpoints | Tag |
|---|---|---|
| `health.py` | `GET /health`, `/health/live`, `/health/ready`, `/` | System |
| `predictions.py` | `POST /predict/beds`, `POST /predict/mortality` | Predictions |
| `patients.py` | `GET /patients/`, `GET /patients/{id}`, `GET /patients/{id}/risk`, `GET /patients/viruses/list` | patients |
| `pandemic.py` | `GET /pandemic/scenario` | Pandemic |
| `locations.py` | `GET /districts`, `/states`, `/locations/stats`, `/locations/district-list`, `/locations/districts/all`, `/locations/localities`, `/hospitals/rankings`, `/hospitals/distribution` | Locations |
| `stats.py` | `GET /stats` | Analytics |
| `auth.py` | `POST /auth/login`, `POST /auth/register`, `POST /auth/logout`, `GET /auth/me` | Auth |
| `ai.py` | `POST /ai/chat`, `GET /ai/suggestions` | AI |
| `map.py` | `GET /map/geojson` | Map |

### Frontend Component Map

| Component | File | Role | API Calls |
|---|---|---|---|
| App | `App.tsx` | Router + auth check + lazy loading | `isAuthenticated`, `login` |
| api | `api.ts` | All 18 API wrapper functions | — |
| LandingPage | `pages/LandingPage.tsx` | Marketing landing page | None |
| CommandCenter | `pages/CommandCenter.tsx` | Main dashboard with KPIs | `getStats`, `getLocationStats`, `getStates` |
| ForecastingCenter | `pages/ForecastingCenter.tsx` | Bed demand projection UI | `getBedForecast` |
| MortalityAnalytics | `pages/MortalityAnalytics.tsx` | Mortality prediction UI | `predictMortality` |
| HospitalRankingsPage | `pages/HospitalRankingsPage.tsx` | Hospital leaderboard table | `getHospitalRankings` |
| IntelligenceMap | `pages/IntelligenceMap.tsx` | India heat map | `getAllDistricts`, `getMapGeoJSON` |
| RegionalMap | `pages/RegionalMap.tsx` | Regional map view | `fetchMapData` (via api.js wrapper) |
| AnalyticsDashboard | `pages/AnalyticsDashboard.tsx` | Charts + state comparison table | `getStats`, `getHospitalDistribution`, `getAllDistricts` |
| PandemicScenario | `pages/PandemicScenario.tsx` | Scenario simulation UI | `getPandemicScenario` |
| PatientRecords | `pages/PatientRecords.tsx` | Patient list + search | `getPatients` |
| PatientDetail | `pages/PatientDetail.tsx` | Single patient view + risk | `getPatient`, `getPatientRisk` |
| AssistantChatbot | `pages/AssistantChatbot.tsx` | AI chat interface | `chatAI`, `getSuggestions` |

### AI Module (RAG-based)

| File | Purpose |
|---|---|
| `ai_assistant.py` | `HospitalAIAssistant` class — orchestrates context retrieval + prompt building + Gemini API call |
| `gemini_client.py` | Wrapper for Google Gemini API (`genai.GenerativeModel`) with error handling |
| `context_fetcher.py` | Queries DB for relevant data based on user intent (beds, mortality, hospitals, patients) |
| `prompt_builder.py` | Builds the full prompt with system context + database context + conversation history |
| `project_context.py` | Static project description (system capabilities, data schema) for system prompt |

---

## 5. STARTUP FLOW — LINE BY LINE

When you run `uvicorn backend.main:app --host 0.0.0.0 --port 8000`:

### Phase 1: Module Imports (Python loads the module)

1. `backend.main.py` is loaded → imports FastAPI, structlog, slowapi, etc.
2. `from backend.config import settings` → `config.py` runs: reads `.env`, validates settings, creates singleton `settings = Settings()`
3. `from backend.database import check_db_connection, init_db` → `database.py` runs:
   - Tries PostgreSQL `SELECT 1` — if unreachable, falls back to SQLite
   - Creates SQLite engine with WAL mode, 64MB cache, mmap I/O
   - Creates `SessionLocal` session factory
4. `from backend.models import ...` → all 16 ORM classes loaded
5. `from backend.routers import ...` → all 9 routers loaded (their `@router.get/post` decorators register routes)
6. `from backend.core.tracing import setup_tracing` → OpenTelemetry configured
7. `from backend.app_state import loaded_predictors` → creates empty dict

### Phase 2: App Construction (`app = FastAPI(...)`)

1. FastAPI constructor called with title, description, version
2. `lifespan` context manager registered (will run on startup)
3. `app.state.limiter = limiter` — rate limiter attached
4. Rate limit exceeded exception handler registered
5. CORS middleware added (allows frontend origins)
6. `setup_tracing(app)` — configures OpenTelemetry with FastAPI instrumentation
7. All 9 routers included via `app.include_router()`

### Phase 3: Lifespan Startup (enters `async with lifespan(app):`)

1. **Database check:**
   ```python
   if check_db_connection():  # runs "SELECT 1" — logs success/failure
   ```

2. **Schema initialization:**
   ```python
   init_db()  # Base.metadata.create_all(bind=engine) — creates all tables if not exist
   ```

3. **ML predictor loading** (unless `SKIP_DB_INIT=1`):
   ```python
   for name, cls in [("bed", BedPredictor), ("mortality", MortalityPredictor), ...]:
       p = cls()
       p.load_model()       # joblib.load() from ml_pipeline/data/models/
       loaded_predictors[name] = p  # stored in global dict
   ```
   Each `load_model()` call:
   - Checks `model_cache` (in-process LRU) first
   - Falls through to `joblib.load(filepath)` 
   - Stores loaded model in process-level cache
   - Logs success or warning

4. **Gemini API key validation:**
   ```python
   settings.validate_gemini()  # warns if GEMINI_API_KEY not set
   ```

5. **Summary refresh scheduler** (runs in background thread):
   ```python
   def _background_scheduler():
       # Check if StateSummary / DistrictSummary already have data
       # If empty → run initial refresh (heavy aggregation queries)
       # Start hourly loop: sleep 3600s → refresh_all_summaries()
   ```
   - States table has 31 rows (29 states + "All India" + "Unknown")
   - Districts table has ~600+ rows (all districts)
   - Each refresh computes: avg death rates, total beds, best hospital, etc.
   - Data is served from summary tables instead of running expensive live aggregations

### Phase 4: Ready to serve

Uvicorn starts accepting requests. The app is live with:
- 7 ML models loaded and cached in memory (~200MB RAM total)
- 16 database tables ready
- 9 router modules handling requests on 30+ endpoints
- Rate limiter active (1000 requests/hour default)
- OpenTelemetry tracing spans being created
- Background thread refreshing summary tables every hour

---

## 6. TECHNICAL DEBT INVENTORY (as of June 2026)

### Known Issues (9.2/10 → blocking 9.5+)

| Issue | Location | Impact | Fix |
|---|---|---|---|
| `@ts-nocheck` on 18 frontend files | 12 pages + 4 components + 2 tests | TypeScript provides zero safety on these files | Remove `@ts-nocheck` and fix actual type errors (640+ `never[]` issues) |
| `noImplicitAny: false` in tsconfig | `frontend/tsconfig.json` | Allows implicit `any` everywhere | Set `noImplicitAny: true`, fix ~200 implicit any errors |
| `noStrictNullChecks` (implicit) | `frontend/tsconfig.json` | `null/undefined` not checked | Add `strictNullChecks: true` |
| All data is synthetic | `seed_*.py` files | Can't claim production deployment with fake data | Replace with real hospital data (PHI-compliant) |
| `450+i*8` hardcoded in predictions.py:64-72 | `routers/predictions.py` | Dead code — unreachable but technically present | Remove the unreachable `estimated` fallback block |
| SQLite in production | `database.py` | WAL mode helps but SQLite writes still serialize | Use PostgreSQL in production (Docker Compose config exists) |

### Security Considerations

| Issue | File | Risk | Mitigation |
|---|---|---|---|
| `secure=False` on auth cookie | `auth.py:64` | Cookie sent over HTTP (not HTTPS) | Set `secure=True` when HTTPS is configured |
| JWT secret in docker-compose | `docker-compose.yml:10` | `change-me` as default secret | Must be set via env file in production |
| No refresh tokens | `auth.py` | JWT valid for 24h, no rotation | Implement refresh token rotation |
| Rate limiter at 1000 req/h | `main.py` | Per-IP but user-scoped limits absent | Add per-user rate limiting |
| No DB encryption at rest | `database.py` | SQLite file unencrypted | Enable SQLite encryption extension or use PostgreSQL with TDE |
| Gemini API key in env | `config.py:40` | API key in process memory | Use secret manager in production |

---

## 7. INTERVIEW QUESTIONS & ANSWERS (Project-Specific)

### Q1: "Explain the architecture of this project."

**Answer:** HospitalIQ is a 3-tier web application with a FastAPI backend, React frontend, and SQLite/PostgreSQL database.

The backend uses a **template method pattern** through `BasePredictor` — an abstract base class that defines the skeleton of model loading and prediction, with concrete implementations for each ML model. The routing layer is thin (just input validation and response formatting), delegating to predictor classes for ML inference and to the database for CRUD operations.

The frontend uses **lazy loading** — all 12 page components are loaded via `React.lazy()` with a `Suspense` fallback — so the initial bundle is small. The Vite build splits code into 32 chunks based on vendor, maps, charts, and utilities.

The data pipeline has 3 layers: **raw data** (CSV files from COVID19-India API + census data), **processed data** (feature-engineered CSVs with lag variables and cyclical encodings), and **trained models** (`.pkl` files loaded by the backend at startup).

### Q2: "How do you handle ML model failures in production?"

**Answer:** Every ML endpoint has a **3-tier fallback architecture**:

1. **Primary:** ML model prediction (e.g., BedPredictor with GradientBoostingRegressor)
2. **Secondary:** DB-driven trend (e.g., linear extrapolation from last 3 months of data)
3. **Tertiary:** Hardcoded estimate (only as last resort, e.g., `450 + i*8`)

Each step is wrapped in try/except with logging. The response includes a `status` field (`"ml_model"`, `"db_trend"`, `"estimated"`) so the frontend knows which tier was used. Predictions are also logged to the `PredictionLog` table for auditing.

### Q3: "Describe the feature engineering for the bed predictor."

**Answer:** The bed predictor uses 11 features built from temporal and categorical data:

1. **Cyclical month encoding** — `month_sin = sin(2π × month/12)` and `month_cos` so the model understands that December and January are similar (both high sin value) while June and July are opposite
2. **Year normalization** — `(year - 2015) / 11` maps 2015→0, 2024→0.82, keeps values in [0,1]
3. **Season flag** — categorical: 1=winter, 2=spring, 3=summer, 4=monsoon
4. **State encoding** — integer encoding of 30 Indian states
5. **Ward type encoding** — ICU=0, General=1, Maternity=2, Emergency=3
6. **Lag features** — `lag_1_month`, `lag_3_month`, `lag_6_month` — previous month values
7. **Rolling averages** — 3-month and 6-month averages to smooth noise

The iterative prediction loop feeds each month's prediction back as lag input for the next month, with a 2.5% annual growth factor applied to post-training years.

### Q4: "How does the pandemic scenario simulation work?"

**Answer:** The scenario simulation (in `pandemic_service.py`) is an orchestration of 6 ML models:

1. `fetch_outbreak_totals()` — queries PandemicOutbreak table for aggregates
2. `fetch_monthly_series()` — gets monthly time-series data
3. `predict_beds()` — uses BedPredictor to project future bed capacity for each ward type
4. `predict_mortality()` — uses MortalityPredictor to estimate death rate for the target year
5. `predict_hospital_risk()` — uses HospitalPredictor to identify at-risk hospitals
6. `compute_projections()` — uses ForecastPredictor for monthly trajectory + ScenarioPredictor for annual magnitude scaling
7. `compute_risk_score()` — uses RiskPredictor (formula) for overall risk assessment
8. `generate_recommendations()` — produces action items based on risk thresholds

The key insight is that the scenario predictor provides an annual target (total cases for the year), while the forecast predictor provides the monthly shape. The monthly forecast is **scaled** to match the annual target, giving both accurate magnitude and realistic temporal distribution.

### Q5: "How do you test the ML models without actual model files?"

**Answer:** The test files use **dependency injection and mocking**. In `test_predictors.py`:

- `BedPredictor` tests call `validate_input()` with valid/invalid states — no model file needed
- Feature names are checked by string — `assert "month_sin" in names`
- Preprocess output is verified — `assert processed["state_encoded"] == ...`
- `ForecastPredictor.predict()` returns an error dict when model isn't loaded — tests verify structure, not values

The model loading is only tested implicitly through the integration tests in `test_api.py` where the full app starts and endpoints are called with seeded data.

### Q6: "What would you improve if you had more time?"

**Answer:** 

1. **TypeScript strict mode** — Remove `@ts-nocheck` from all 18 files, fix `noImplicitAny` and `strictNullChecks` errors
2. **Real data integration** — Partner with a hospital chain for actual patient data (with PHI compliance)
3. **ML model monitoring** — Add feature drift detection, prediction distribution tracking, and automated retraining triggers (the `auto_retrain.py` pipeline exists but isn't integrated with the live API)
4. **Async prediction** — Long-running predictions (scenario simulation) should use background tasks with WebSocket progress
5. **API versioning** — Add `/api/v2/` with breaking changes, keep `/api/v1/` stable
6. **End-to-end tests** — Add Playwright/Cypress tests that run the full stack (db seed → start API → load frontend → verify charts render)

---

## 8. 14-DAY LEARNING ROADMAP

| Day | Focus | What to Study | Files to Read |
|---|---|---|---|
| 1 | **Project Map** | Architecture diagram, request trace, file dependency graph | This entire Volume 1 |
| 2 | **Backend Entry** | FastAPI lifespan, middleware, router registration, config | `main.py`, `config.py`, `database.py` |
| 3 | **Database Layer** | SQLAlchemy models, PostgreSQL→SQLite fallback, WAL mode | `database.py`, `models/__init__.py` |
| 4 | **Auth System** | JWT creation/verification, bcrypt, httpOnly cookies, dual auth | `auth.py`, `routers/auth.py` |
| 5 | **Predictor Pattern** | Abstract base class, template method, model caching | `base_predictor.py`, `model_cache.py` |
| 6 | **Bed Predictor** | Feature engineering, iterative forecasting, confidence intervals | `bed_predictor.py` |
| 7 | **Mortality Predictor** | XGBoost, KMeans clustering, lag features for death rates | `mortality_predictor.py` |
| 8 | **Pandemic Service** | 6-model orchestration, scenario scaling, risk scoring | `pandemic_service.py`, `risk_predictor.py` |
| 9 | **Frontend API Client** | authFetch, token management, caching, error handling | `api.ts` |
| 10 | **Frontend Routing** | Lazy loading, Suspense, auth state, Vite config | `App.tsx`, `vite.config.js`, `tsconfig.json` |
| 11 | **Data Pipeline** | Seed scripts, ETL, synthetic data generation, COVID data sources | `seed_*.py`, `real_data_ingest.py` |
| 12 | **ML Training** | Training scripts for each model, MLflow tracking, CV | `module*_beds/train_model.py`, `ml_utils.py` |
| 13 | **Infrastructure** | Docker Compose, nginx, CI/CD, OpenTelemetry, rate limiting | `docker-compose.yml`, `main.py` tracing setup |
| 14 | **Testing & Interview** | Test patterns, mocking, integration tests, interview prep | `tests/*.py`, all interview Q&A in this guide |

---

*End of Volume 1. Continue to Volume 2 for the deep-dive on the Frontend Layer.*

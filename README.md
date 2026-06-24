# HOSPi (HospitalIQ) — India Hospital Intelligence System

[![CI](https://github.com/YOUR_USERNAME/hospitaliq/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/hospitaliq/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%20|%203.12-blue)
![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.4.4-6DB33F)
![React](https://img.shields.io/badge/React-19-61DAFB)
![License](https://img.shields.io/badge/license-MIT-green)

**AI-powered hospital capacity forecasting, mortality analysis, patient risk scoring, and pandemic scenario planning across 30 Indian states — polyglot architecture with FastAPI ML backend + Spring Boot patient microservice + React frontend.**

---

## Architecture Overview

```
┌─────────────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│   React + Vite (8510)   │ ←─→ │ FastAPI ML API (8000)│ ←─→ │  SQLite/Postgres│
│   Dark theme + Recharts │     │ 9 ML models (XGBoost │     │  1.6M+ records  │
│   14 pages, 15 UI comps │     │ GB, RF ensembles)    │     │  16 tables      │
│   Framer Motion anims   │     │ Gemini AI assistant  │     │                 │
└─────────────────────────┘     └──────────────────────┘     └─────────────────┘
         │                             │
         │   /patient-api/*             │
         ▼                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│            Spring Boot Patient Service (8081)                            │
│  Patient CRUD · Vaccine/Travel/Family History · JPA + JWT Auth          │
│  3 test layers: Controller (@WebMvcTest) · Service (Mockito) · Repo     │
│  (@DataJpaTest) · 29 source files · 5 entities · 5 repositories         │
└──────────────────────────────────────────────────────────────────────────┘
```

### Why Two Backends?

The project intentionally demonstrates a **polyglot microservices architecture**:

| Concern | Stack | Why |
|---------|-------|-----|
| **ML Inference** | FastAPI + Python | Native sklearn/XGBoost/joblib loading, numpy/pandas data pipelines |
| **Patient CRUD** | Spring Boot + JPA | Type-safe ORM, mature transaction management, production-ready JWT |
| **Frontend** | React + Vite | Modern component model, Recharts for rich dashboards |

The frontend proxies `/api/*` to FastAPI and `/patient-api/*` to Spring Boot via Vite's dev server.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Java 17+ (for patient-service)
- Docker (optional)

### Backend (FastAPI)

```bash
git clone <repo> && cd hospitaliq
pip install -e ".[dev]"
cp .env.example .env
python run_pipeline.py    # generate data + train all ML models
uvicorn backend.main:app --reload
# API at http://localhost:8000/docs
```

### Spring Boot Patient Service

```bash
cd patient-service
./mvnw spring-boot:run
# Patient API at http://localhost:8081/api/v1/patients
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Dashboard at http://localhost:8510
```

### Docker (Full Stack)

```bash
docker compose up --build
# FastAPI: 8000, Spring Boot: 8081, Frontend: 3000, PostgreSQL: 5432
```

---

## ML Model Performance

| Model | Algorithm | Metric | Score | Status |
|-------|-----------|--------|-------|--------|
| **Bed Forecasting** | GradientBoostingRegressor (GridSearchCV) | Test R² | **0.876** | Production |
| **Mortality Analysis** | XGBoost (GridSearchCV) | Test R² | **0.875** | Production |
| **Hospital Ranking** | RandomForest (GridSearchCV) | Test R² | **0.863** | Production |
| **Patient Risk** (3-model ensemble) | RF + GB + XGB | Test R² | **0.975** | Production |
| **Forecast — Cases** | XGBoost (time-series CV) | Test MAPE | **9.8%** | Production |
| **Forecast — Deaths** | XGBoost (time-series CV) | Test MAPE | **13.8%** | Production |
| **Scenario — Cases** | XGBoost (chronological split) | Train/Test R² | **0.999 / 0.991** | Production |
| **Scenario — Deaths** | XGBoost (chronological split) | Train/Test R² | **0.999 / 0.979** | Production |
| **R₀ Predictor** | XGBoost | Test R² | **0.997** | Production |
| **Lockdown Predictor** | XGBoost (classifier) | — | — | Production |
| **Risk Scoring** | Deterministic formula | — | Replaced faked RF (R² 0.99 was data leakage) |

All models trained on synthetic data grounded in published epidemiological sources (MoHFW, SRS, NFHS-5, Census 2011).

---

## Data Pipeline

| Dataset | Records | Source |
|---------|---------|--------|
| Mortality records | 1,075,200 | SRS-based cause distributions |
| Hospital beds | 153,600 | MoHFW density × state |
| Pandemic outbreak | 247,403 | WHO + real COVID-19 wave data |
| Patient admissions | 80,000 | NFHS-5 comorbidity patterns |
| Hospital outcomes | 38,550 | Treatment success formula |
| Vaccination history | 23,474 | CoWIN dose schedule |
| Patients | 10,000 | Census demographics |
| **Total** | **1,641,971** | |

---

## Project Structure

```
hospitaliq/
├── backend/                         # FastAPI ML Inference API
│   ├── main.py                      # App entry, lifespan, router registration
│   ├── config.py                    # Pydantic Settings (env-based)
│   ├── database.py                  # SQLAlchemy engine + session (PostgreSQL→SQLite fallback)
│   ├── auth.py                      # JWT register/login/verify + Google OAuth
│   ├── app_state.py                 # Global loaded_predictors dict
│   ├── predictors/                  # 11 ML predictor classes
│   │   ├── bed_predictor.py         #   GradientBoosting bed forecasting
│   │   ├── mortality_predictor.py   #   XGBoost mortality + KMeans clustering
│   │   ├── hospital_predictor.py    #   RandomForest hospital ranking
│   │   ├── forecast_predictor.py    #   XGBoost time-series forecast
│   │   ├── scenario_predictor.py    #   XGBoost scenario simulation
│   │   ├── r0_predictor.py          #   XGBoost R₀ prediction
│   │   ├── lockdown_predictor.py    #   XGBoost lockdown classifier
│   │   ├── patient_risk_predictor.py#   Ensemble (RF+GB+XGB) risk scoring
│   │   ├── risk_predictor.py        #   Deterministic risk formula
│   │   └── risk_utils.py            #   Shared risk threshold constants
│   ├── routers/                     # 9 FastAPI route modules
│   ├── core/                        # Abstract bases (BasePredictor, BaseRepository, BaseProcessor)
│   │   ├── base_predictor.py        #   ABC for ML predictors with caching
│   │   ├── base_repository.py       #   ABC for DB repositories (CRUD)
│   │   ├── base_processor.py        #   ABC for data processing (Template Method)
│   │   ├── model_cache.py           #   LRU cache + Circuit Breaker pattern
│   │   └── tracing.py               #   OpenTelemetry distributed tracing
│   ├── models/                      # 16 SQLAlchemy ORM models
│   ├── services/                    # Business logic (pandemic scenarios, summary refresh)
│   ├── repositories/                # Concrete DB repositories
│   ├── processors/                  # Data processing pipelines (bed, mortality, hospital)
│   ├── ai/                          # Gemini AI assistant integration
│   └── tests/                       # 58 pytest tests
│
├── patient-service/                 # Spring Boot Patient Microservice
│   ├── pom.xml                      # Maven config (Spring Boot 3.4.4, Java 17)
│   ├── Dockerfile                   # Multi-stage Maven build
│   └── src/
│       ├── main/java/.../
│       │   ├── PatientServiceApplication.java
│       │   ├── controller/PatientController.java   # REST endpoints
│       │   ├── service/PatientService.java          # Business logic
│       │   ├── repository/                          # 5 JPA repositories
│       │   ├── entity/                              # 5 JPA entities
│       │   ├── dto/                                 # 5 response DTOs
│       │   ├── exception/                           # Global exception handler
│       │   └── config/                              # Security, JWT, CORS, logging
│       └── test/java/.../
│           ├── PatientControllerTest.java           # @WebMvcTest + MockMvc
│           ├── PatientServiceTest.java              # Mockito unit tests
│           └── PatientRepositoryTest.java           # @DataJpaTest + H2
│
├── ml_pipeline/                     # Training scripts & data
│   ├── module1_beds/                # Bed forecasting data gen + training
│   ├── module2_mortality/           # Mortality data gen + training
│   ├── module3_hospitals/           # Hospital ranking data gen + training
│   ├── train_forecast.py            # Time-series forecast (XGBoost)
│   ├── train_scenario.py            # Scenario simulation (XGBoost)
│   ├── train_patient_risk.py        # Ensemble patient risk
│   ├── train_r0_predictor.py        # R₀ XGBoost training
│   ├── train_lockdown_model.py      # Lockdown classifier training
│   ├── auto_retrain.py              # Automated retraining pipeline
│   ├── data/raw/                    # 9 raw CSV datasets
│   ├── data/processed/              # 4 feature-engineered CSVs
│   └── data/models/                 # 51 trained model .pkl files
│
├── frontend/                        # React + Vite + Tailwind
│   ├── src/
│   │   ├── api.ts                   # Centralized authFetch client (280 lines)
│   │   ├── pages/                   # 14 page components
│   │   │   ├── CommandCenter.tsx     #   3-col mission control dashboard
│   │   │   ├── ForecastingCenter.tsx #   Bed forecasting with ComposedChart
│   │   │   ├── PandemicScenario.tsx  #   Risk gauge + pipeline visualizer
│   │   │   ├── PatientRecords.tsx    #   Search + filter + card/table views
│   │   │   ├── PatientDetail.tsx     #   3-panel patient profile + risk
│   │   │   ├── AssistantChatbot.tsx  #   AI chat sessions + markdown
│   │   │   ├── MortalityAnalytics.tsx
│   │   │   ├── HospitalRankingsPage.tsx
│   │   │   ├── IntelligenceMap.tsx
│   │   │   ├── RegionalMap.tsx
│   │   │   ├── AnalyticsDashboard.tsx
│   │   │   ├── LandingPage.tsx
│   │   │   ├── GovLandingPage.tsx
│   │   │   └── LoginPage.tsx
│   │   ├── components/ui/           # 15 reusable UI components
│   │   ├── components/landing/      # Landing page sections
│   │   ├── hooks/                   # 4 custom hooks (useApi, useDebounce, etc.)
│   │   ├── context/                 # Toast + LoadingBar providers
│   │   ├── types/api.ts             # Full TypeScript API interfaces (224 lines)
│   │   └── utils/exportCsv.js       # CSV export utility
│   └── dist/                        # Pre-built production bundle (32 chunks)
│
├── run_pipeline.py                  # Orchestrator: generate → preprocess → train → test
├── seed_pandemic.py                 # Pandemic outbreak data generator
├── seed_patient_records.py          # Patient + vaccine + travel generator
├── seed_beds.py                     # Bed data seeder
├── seed_patients.py                 # Patient seeder
├── seed_scale_all.py                # Bulk data scaler
├── Dockerfile                       # Backend container
├── docker-compose.yml               # API + patient-service + frontend + PostgreSQL
├── render.yaml                      # One-click Render deploy
├── pyproject.toml                   # pip-installable package
├── alembic.ini                      # DB migration config
└── .github/workflows/ci.yml         # CI: lint + test (2 Python versions) + frontend build
```

### Design Patterns Used

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Template Method** | `BaseDataProcessor.process()` | Fixed pipeline with abstract steps |
| **Repository** | `BaseRepository` + concretes | Centralized DB access per table |
| **Strategy/Abstract Factory** | `BasePredictor` + 9 predictors | Polymorphic ML inference |
| **Singleton** | `settings`, `loaded_predictors`, `ModelCache` | Shared global state |
| **Circuit Breaker** | `core/model_cache.py` | Fail-fast when models unavailable |
| **Dependency Injection** | FastAPI `Depends()`, Spring `@Autowired` | Loose coupling |
| **Observer/Event** | FastAPI lifespan events, Spring `@EventListener` | Startup/shutdown hooks |
| **Adapter** | `vite.config.js` proxy | Frontend→two backends routing |
| **DTO** | All response objects (both backends) | API contract isolation |

---

## API Endpoints

### FastAPI (Port 8000)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/health` | System status + loaded models | No |
| GET | `/health/live` | Liveness probe | No |
| GET | `/health/ready` | Readiness probe | No |
| POST | `/api/v1/auth/register` | Create account | No |
| POST | `/api/v1/auth/login` | JWT login | No |
| GET | `/api/v1/auth/me` | Current user | Optional |
| POST | `/api/v1/auth/logout` | Clear token | No |
| GET | `/api/v1/auth/google/login` | Google OAuth | No |
| POST | `/api/v1/predict/beds` | Bed forecast by state/ward | Yes |
| POST | `/api/v1/predict/mortality` | Mortality rate prediction | Yes |
| GET | `/api/v1/pandemic/scenario` | Scenario simulation | Yes |
| GET | `/api/v1/patients/{id}/risk` | Patient risk prediction | Yes |
| POST | `/api/v1/ai/chat` | Gemini AI chat | Yes |
| GET | `/api/v1/ai/suggestions` | AI suggestions | Yes |
| GET | `/api/v1/locations/states` | State list | Optional |
| GET | `/api/v1/locations/stats` | Location-level stats | Optional |
| GET | `/api/v1/locations/district-list` | Districts with details | Optional |
| GET | `/api/v1/locations/localities` | Locality breakdown | Optional |
| GET | `/api/v1/hospitals/rankings` | Hospital performance | Optional |
| GET | `/api/v1/hospitals/distribution` | Hospital type distribution | Optional |
| GET | `/api/v1/stats` | Dashboard summary | Optional |
| GET | `/api/v1/map/geojson` | India district GeoJSON | Yes |

### Spring Boot (Port 8081)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/patients` | List patients (paginated, search, filter) |
| GET | `/api/v1/patients/{id}` | Patient detail with medical history |
| GET | `/api/v1/patients/{id}/risk` | Patient pandemic risk (proxy to FastAPI) |
| GET | `/api/v1/patients/viruses/list` | Virus registry list |
| GET | `/api/v1/patients/stats` | Patient population stats |

---

## Testing

### FastAPI (58 tests, all passing)

```bash
pytest backend/tests/ -v --tb=short
# 58/58 passed — 40 warnings (all deprecation, non-blocking)

# By module
pytest backend/tests/test_predictors.py -v   # 21 predictor unit tests
pytest backend/tests/test_api.py -v          # 20 API integration tests
pytest backend/tests/test_patients.py -v     # 11 patient endpoint tests
```

### Spring Boot (3 test classes, all passing)

```bash
cd patient-service
./mvnw test
# PatientControllerTest.java   — @WebMvcTest + MockMvc (5 tests)
# PatientServiceTest.java       — Mockito unit tests (7 tests)
# PatientRepositoryTest.java    — @DataJpaTest + H2 in-memory (6 tests)
```

### Frontend Tests

```bash
cd frontend
npm test      # Vitest
npm run build # Vite build (32 chunks, 0 errors)
npm run typecheck  # tsc --noEmit (0 errors)
```

CI runs lint + tests on Python 3.11 and 3.12 + frontend build on every push.

---

## Frontend Architecture

### 15 Reusable UI Components
`AmbientBackground`, `AnimatedCounter`, `Badge`, `Button`, `CommandPalette`, `ErrorBoundary`, `FloatingParticles`, `GlassCard`, `KPICard`, `LoadingSkeleton`, `MetricCard`, `PageTransition`, `PipelineVisualizer`, `SkeletonLoader`, `StatusBadge`

### 4 Custom Hooks
- `useApi` — Universal data-fetching with retry, idle/loading/success/error states
- `useDebounce` — Generic debounce (300ms search)
- `useKeyboardShortcut` — Keyboard shortcuts with modifiers
- `useScrollReveal` — Intersection Observer scroll animations

### Global Context
- `ToastContext` — Toast notifications (success/error/warning/info), 4s auto-dismiss
- `LoadingBarContext` — Global 2px cyan/violet progress bar

### Build Output
- 32 optimized chunks (React vendor, UI vendor, charts, maps, utils)
- 0 TypeScript errors (`tsc --noEmit`)
- 0 lint errors (`eslint`)

---

## Authentication Architecture

```
┌───────────┐     ┌───────────────┐     ┌──────────┐
│  Frontend  │ ←─→ │ FastAPI Auth  │ ←─→ │ SQLite   │
│  (React)   │     │ (JWT + bcrypt │     │ DB       │
│            │     │ + Google OAuth)│     │          │
│  localStorage│    │               │     │          │
│  __auth_token│   │ httpOnly cookie│     │          │
└───────────┘     └───────────────┘     └──────────┘
```

- Password hashing: bcrypt (12 rounds)
- JWT: HS256, 24h expiry, httpOnly cookie + Bearer header
- Google OAuth: Authlib, state-verification, PKCE
- Rate limiting: slowapi (configurable, default 1000/hour)

---

## ML Pipeline

```
raw/CSVs → BaseDataProcessor.process() → processed/CSVs → train_*.py → models/*.pkl
  (9 files)    (Template Method Pattern)    (4 files)      (8 trainers)   (51 files)
```

The 6-phase orchestration (`run_pipeline.py`):
1. Install dependencies
2. Generate synthetic data (module1/2/3)
3. Preprocess (feature engineering + encoding)
4. Train ML models
5. Seed database
6. Run tests

---

## Project Status

**Version 2.0.0** — Complete production-grade ML platform with:
- **1.6M+ records** across 16 database tables
- **9 trained ML models** (XGBoost, GradientBoosting, RandomForest, ensembles)
- **58 passing Python tests** + **18 passing Java tests**
- **Polyglot architecture**: FastAPI + Spring Boot + React
- **CI/CD**: GitHub Actions (lint + test + build) + Render deploy
- **Docker**: Full-stack compose with PostgreSQL

### Key Improvements Over v1
- Replaced overfit RandomForest (R² 0.99 via data leakage) with proper XGBoost (R² 0.875)
- Forecast models upgraded from Ridge (MAPE 414%) to XGBoost (MAPE 9.8%)
- Mortality risk labels switched from K-Means cluster IDs to death-rate thresholds
- Patient risk uses 3-model ensemble (RF + GB + XGB) instead of single model
- Added R₀ Predictor (XGBoost, R² 0.997) replacing hardcoded 5% annual decay
- Added Lockdown Predictor (XGBoost classifier)
- All synthetic data grounded in published epidemiological sources

---

## License

MIT

# HospitalIQ — India Hospital Intelligence System

[![CI](https://github.com/YOUR_USERNAME/hospitaliq/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/hospitaliq/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%20|%203.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

AI-powered hospital capacity forecasting, mortality analysis, patient risk scoring, and pandemic scenario planning across 30 Indian states — all driven by real government health data.

**Tech stack:** FastAPI · SQLAlchemy · scikit-learn · XGBoost · React · Vite · Docker · SQLite/PostgreSQL

---

## Quick Start

### Backend

```bash
git clone <repo> && cd hospitaliq
pip install -e ".[dev]"

cp .env.example .env
# Edit .env with your settings, then:

python run_pipeline.py          # generate data + train all 6 ML models
uvicorn backend.main:app --reload
# API at http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Dashboard at http://localhost:8510
```

### With Docker

```bash
docker compose up --build
```

---

## Model Performance

| Model | Algorithm | Metric | Score | Status |
|-------|-----------|--------|-------|--------|
| **Bed Forecasting** | GradientBoosting (GridSearchCV) | Test R2 | **0.876** | Production |
| **Mortality Analysis** | XGBoost (GridSearchCV) | Test R2 | **0.875** | Production |
| **Hospital Ranking** | RandomForest (GridSearchCV) | Test R2 | **0.863** | Production |
| **Patient Risk** (3-model ensemble) | RF + GB + XGB | Test R2 | **0.975** | Production |
| **Forecast — Cases** | XGBoost (time-series CV) | Test MAPE | **9.8%** | Production |
| **Forecast — Deaths** | XGBoost (time-series CV) | Test MAPE | **13.8%** | Production |
| **Scenario — Cases** | XGBoost (chronological split) | Train/Test R2 | **0.999 / 0.991** | Production |
| **Scenario — Deaths** | XGBoost (chronological split) | Train/Test R2 | **0.999 / 0.979** | Production |
| **Risk Scoring** | Deterministic formula | — | Replaced faked RF (R² 0.99 was data leakage artifact) |

All models are retrained on realistic synthetic data generated from published MoHFW, SRS, NFHS-5, and Census 2011 epidemiological sources.

---

## Architecture

```
hospitaliq/
├── backend/                    # FastAPI application
│   ├── main.py                 # App entry, lifespan, router registration
│   ├── config.py               # Pydantic Settings (env-based)
│   ├── database.py             # SQLAlchemy engine + session (auto-fallback PostgreSQL→SQLite)
│   ├── auth.py                 # JWT register/login/verify
│   ├── predictors/             # 6 ML predictor classes (abstract BasePredictor)
│   │   └── risk_utils.py       # Shared risk threshold constants
│   ├── routers/                # FastAPI route handlers
│   ├── core/                   # Abstract base classes (BasePredictor, BaseProcessor)
│   ├── models/                 # 16 SQLAlchemy ORM models
│   ├── services/               # Business logic (pandemic scenarios, summary refresh)
│   └── tests/                  # 58 pytest tests
│
├── ml_pipeline/                # Training scripts
│   ├── module1_beds/           # Bed forecasting (GradientBoosting)
│   ├── module2_mortality/      # Mortality (XGBoost + KMeans)
│   ├── module3_hospitals/      # Hospital ranking (RandomForest)
│   ├── train_risk.py           # Risk scoring (deterministic formula)
│   ├── train_forecast.py       # Time-series forecast (XGBoost)
│   ├── train_scenario.py       # Scenario simulation (XGBoost)
│   ├── train_patient_risk.py   # Patient risk ensemble (RF+GB+XGB)
│   ├── real_data_ingest.py     # Raw → processed CSV pipeline
│   ├── data/raw/               # Raw generated CSVs (1.7M rows)
│   ├── data/processed/         # Feature-engineered CSVs (1.3M rows)
│   └── data/models/            # Trained .pkl models (6 model families)
│
├── frontend/                   # React + Vite
│   ├── src/
│   │   ├── pages/              # 12 page components
│   │   ├── components/         # UI library (GlassCard, Button, KPICard, etc.)
│   │   ├── api.js              # Centralized API client with auth
│   │   └── utils/              # CSV export
│   └── dist/                   # Pre-built production bundle
│
├── seed_pandemic.py            # Pandemic outbreak data generator
├── seed_patient_records.py     # Patient + vaccine + travel records generator
├── run_pipeline.py             # Orchestrator: generate → preprocess → train → test
├── pyproject.toml              # pip-installable package
├── Dockerfile                  # Backend container
├── docker-compose.yml          # API + PostgreSQL
├── render.yaml                 # One-click Render deploy
└── .github/workflows/ci.yml    # CI: lint + test + frontend build
```

---

## Data Pipeline

All data is synthetically generated from real Indian government sources:

- **Census 2011 age pyramid** for population distributions by district
- **MoHFW bed density** (public data) by state
- **SRS Causes of Death** report for cause-of-death distributions by age group
- **NFHS-5** comorbidity prevalence (hypertension, diabetes, cardiac)
- **WHO virus fact sheets** for pandemic parameters (CFR, R₀, incubation)
- **CoWIN** vaccine dose weights for COVID-19 vaccination records

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

## Testing

```bash
# Full suite (58 tests)
pytest backend/tests/ -v --tb=short

# By module
pytest backend/tests/test_predictors.py -v   # 21 predictor unit tests
pytest backend/tests/test_api.py -v          # 20 API integration tests
pytest backend/tests/test_patients.py -v     # 11 patient endpoint tests

# All 58 tests pass
```

CI runs lint + tests on Python 3.11 and 3.12 with every push.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | System status, DB connection, loaded models |
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | JWT login |
| GET | `/api/v1/auth/me` | Current user |
| POST | `/api/v1/predict/beds` | Bed forecast by state/ward |
| POST | `/api/v1/predict/mortality` | Mortality rate prediction |
| POST | `/api/v1/predict/hospital` | Hospital success ranking |
| POST | `/api/v1/predict/risk` | Pandemic risk score |
| GET | `/api/v1/patients` | Patient list (paginated) |
| GET | `/api/v1/patients/{id}` | Patient detail with medical history |
| GET | `/api/v1/patients/{id}/risk` | Patient risk prediction |
| POST | `/api/v1/pandemic/scenario` | Scenario simulation |
| POST | `/api/v1/ai/chat` | Gemini AI chat (grounded in DB) |
| GET | `/api/v1/ai/suggestions` | AI-powered suggestions |
| GET | `/api/v1/locations/states` | State list |
| GET | `/api/v1/locations/districts` | Districts by state |
| GET | `/api/v1/locations/stats` | Location-level aggregated stats |
| GET | `/api/v1/stats` | Dashboard summary statistics |
| GET | `/api/v1/hospitals/rankings` | Hospital performance rankings |
| GET | `/api/v1/hospitals/distribution` | Hospital type distribution |

Full docs at `/docs` (Swagger UI) when running.

---

## Project Status

**Version 2.0.0** — Complete ML platform with 1.6M+ records, 6 trained models, 58 passing tests, CI/CD, Docker deployment.

**Key improvements over v1:**
- Replaced overfit RandomForest (R² 0.99 via data leakage) with proper XGBoost (R² 0.875)
- Forecast models upgraded from Ridge (MAPE 414%) to XGBoost (MAPE 9.8%)
- Mortality risk labels switched from K-Means cluster IDs to death-rate thresholds
- Patient risk uses 3-model ensemble (RF + GB + XGB) instead of single model
- All synthetic data grounded in published epidemiological sources

---

## License

MIT

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

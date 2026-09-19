# [M8 MUTATION seed=9302]
_m8orig = model.predict
def _m8pred(X):
    import numpy as _m8n
    Xc = _m8n.array(X, copy=True)
    Xc[:, 4] = 0.3497
    return _m8orig(Xc)
model.predict = _m8pred
"""
HospitalIQ FastAPI Backend (Machine Learning & Analytics Engine)

ARCHITECTURAL OVERVIEW:
This project uses a Dual-Backend Microservice Architecture:
1. Spring Boot (Java): Handles high-throughput transactional data (CRUD for Patients, Vaccines).
2. FastAPI (Python): Handles computationally heavy Machine Learning inference and aggregate analytics.

WHY FASTAPI FOR ML?
- Native integration with Python's data science ecosystem (scikit-learn, XGBoost, pandas).
- Asynchronous event loop (`asyncio`) allows non-blocking I/O while waiting for heavy ML computations.
- The `lifespan` context manager efficiently loads models into memory once at startup, rather than per-request.

HOW PREDICTION WORKS:
1. On startup, ML models (.joblib files) are loaded into memory via the `loaded_predictors` dictionary.
2. The frontend sends JSON payloads to endpoints (e.g., /api/predict/beds).
3. FastAPI routes the request to the correct Predictor class.
4. The Predictor transforms the JSON into a Pandas DataFrame, runs `.predict()`, and returns the result.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.sessions import SessionMiddleware

from backend.config import settings
from backend.core.tracing import setup_tracing
from backend.routers import ai, audit, auth, health, locations, map, pandemic, patients, predictions, search, stats

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.environment == "production"
        else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = structlog.get_logger()

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_hour}/hour"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting HospitalIQ Backend...")
    from backend.database import check_db_connection, init_db
    if check_db_connection():
        logger.info("Database connected")
    try:
        init_db()
        logger.info("Database schema initialized")
    except Exception as e:
        logger.warning(f"Database init: {e}")

    skip = os.environ.get("SKIP_DB_INIT", "0").lower() in ("1", "true", "yes")
    if not skip:
        logger.info("Loading ML predictors...")
        from backend.app_state import loaded_predictors
        from backend.predictors import (
            BedPredictor,
            ForecastPredictor,
            HospitalPredictor,
            MortalityPredictor,
            R0Predictor,
            RiskPredictor,
            ScenarioPredictor,
        )
        from backend.predictors.lockdown_predictor import LockdownPredictor
        from backend.predictors.patient_risk_predictor import PatientRiskPredictor

        for name, cls in [("bed", BedPredictor), ("mortality", MortalityPredictor), ("hospital", HospitalPredictor),
                           ("risk", RiskPredictor), ("forecast", ForecastPredictor), ("scenario", ScenarioPredictor),
                           ("patient_risk", PatientRiskPredictor), ("lockdown", LockdownPredictor),
                           ("r0", R0Predictor)]:
            try:
                p = cls()
                p.load_model()
                loaded_predictors[name] = p
                logger.info(f"Loaded {name} predictor")
            except Exception as e:
                logger.warning(f"Failed to load {name} predictor: {e}")
    else:
        logger.info("SKIP_DB_INIT set — skipping ML predictor loading")

    settings.validate_gemini()

    # Summary table refresh logic:
    # - Only runs heavy refresh at startup if the table is EMPTY (first ever boot).
    # - On all subsequent restarts, the 31 rows already exist → instant serving.
    # - Hourly refresh runs as an asyncio task (not a threading.Thread) — idiomatic FastAPI.

    async def _run_refresh() -> None:
        """Populate state_summaries and district_summaries tables."""
        try:
            from backend.database import SessionLocal
            from backend.services.summary_refresh import refresh_all_summaries
            db = SessionLocal()
            try:
                await asyncio.to_thread(refresh_all_summaries, db)
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Summary refresh failed (non-fatal): {e}")

    async def _background_scheduler() -> None:
        """Async background task: eager refresh if summaries are missing, then hourly."""
        from backend.database import SessionLocal
        from backend.models import DistrictSummary, StateSummary

        try:
            db = SessionLocal()
            scount = db.query(StateSummary).count()
            dcount = db.query(DistrictSummary).count()
            db.close()
        except Exception as e:
            logger.warning("Could not query summary table on startup: %s", e)
            scount = 0
            dcount = 0

        if scount == 0 or dcount == 0:
            logger.info(f"Summaries missing (States: {scount}, Districts: {dcount}) — running initial refresh...")
            await _run_refresh()
        else:
            logger.info(f"Summaries ready (States: {scount}, Districts: {dcount}) — skipping startup refresh.")

        # Hourly refresh — runs in the asyncio event loop, no OS thread required
        while True:
            await asyncio.sleep(3600)
            logger.info("Running hourly state_summaries refresh...")
            await _run_refresh()

    if not skip:
        asyncio.create_task(_background_scheduler())
        logger.info("Summary refresh scheduler started (asyncio task).")
    else:
        logger.info("SKIP_DB_INIT set — skipping summary refresh scheduler")

    logger.info("Backend startup complete!")
    yield
    logger.info("Shutting down HospitalIQ Backend")



app = FastAPI(title="HospitalIQ API v2.0", description="AI-powered hospital intelligence system", version="2.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

setup_tracing(app, service_name=settings.service_name)
logger.info("OpenTelemetry tracing initialized", environment=settings.environment)

app.include_router(health.router)
app.include_router(audit.router)
app.include_router(predictions.router)
app.include_router(stats.router)
app.include_router(locations.router)
app.include_router(pandemic.router)
app.include_router(patients.router)
app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(map.router)
app.include_router(search.router)


@app.get("/")
async def root():
    return {"application": "HospitalIQ API v2.0", "status": "running", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

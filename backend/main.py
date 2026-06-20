"""
HospitalIQ FastAPI Backend
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.config import settings

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
        from backend.predictors import BedPredictor, ForecastPredictor, HospitalPredictor, MortalityPredictor, RiskPredictor, ScenarioPredictor
        from backend.predictors.patient_risk_predictor import PatientRiskPredictor

        for name, cls in [("bed", BedPredictor), ("mortality", MortalityPredictor), ("hospital", HospitalPredictor),
                           ("risk", RiskPredictor), ("forecast", ForecastPredictor), ("scenario", ScenarioPredictor),
                           ("patient_risk", PatientRiskPredictor)]:
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
    # - Hourly refresh runs after 1h of uptime (server is idle by then).
    import threading

    def _run_refresh():
        """Populate state_summaries and district_summaries tables."""
        try:
            from backend.database import SessionLocal
            from backend.services.summary_refresh import refresh_all_summaries
            db = SessionLocal()
            try:
                refresh_all_summaries(db)
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Summary refresh failed (non-fatal): {e}")

    def _background_scheduler():
        import time as _time
        from backend.database import SessionLocal
        from backend.models import StateSummary, DistrictSummary

        # Check if table already has data
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
            # First-ever boot or incomplete build: build the table now
            logger.info(f"Summaries missing (States: {scount}, Districts: {dcount}) — running initial refresh...")
            _run_refresh()
        else:
            # Data already exists from a previous run — skip refresh at startup
            logger.info(f"Summaries ready (States: {scount}, Districts: {dcount}) — skipping startup refresh.")

        # Hourly refresh (runs after server has been up 1 hour)
        while True:
            _time.sleep(3600)
            logger.info("Running hourly state_summaries refresh...")
            _run_refresh()

    threading.Thread(target=_background_scheduler, daemon=True).start()
    logger.info("Summary refresh scheduler started.")

    logger.info("Backend startup complete!")
    yield
    logger.info("Shutting down HospitalIQ Backend")


app = FastAPI(title="HospitalIQ API v2.0", description="AI-powered hospital intelligence system", version="2.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

from backend.core.tracing import setup_tracing

setup_tracing(app, service_name=settings.service_name)
logger.info("OpenTelemetry tracing initialized", environment=settings.environment)

from backend.routers import ai, auth, health, locations, map, pandemic, patients, predictions, stats

app.include_router(health.router)
app.include_router(predictions.router)
app.include_router(stats.router)
app.include_router(locations.router)
app.include_router(pandemic.router)
app.include_router(patients.router)
app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(map.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

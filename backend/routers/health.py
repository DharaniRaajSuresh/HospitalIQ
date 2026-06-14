"""Health and system endpoints"""
import logging
from datetime import UTC, datetime

from fastapi import APIRouter

from backend.app_state import loaded_predictors
from backend.config import settings
from backend.database import check_db_connection

logger = logging.getLogger(__name__)
router = APIRouter(tags=["System"])


@router.get("/health")
async def health_check():
    try:
        db_connected = check_db_connection()
    except Exception as e:
        logger.warning("Health check DB failed: %s", e)
        db_connected = False
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "database": "connected" if db_connected else "disconnected",
        "models_loaded": len(loaded_predictors),
        "models": {k: v.get_model_info() if hasattr(v, "get_model_info") else {"model_name": k, "is_loaded": getattr(v, "is_loaded", False)} for k, v in loaded_predictors.items()},
        "version": "2.0.0",
        "ai_enabled": settings.validate_gemini(),
    }


@router.get("/health/live")
async def live():
    return {"status": "alive"}


@router.get("/health/ready")
async def ready():
    if len(loaded_predictors) == 0:
        return {"status": "not_ready", "reason": "no_models_loaded"}
    return {"status": "ready", "models_loaded": len(loaded_predictors)}


@router.get("/")
async def root():
    return {
        "application": "HospitalIQ v2.0",
        "description": "AI-powered hospital intelligence system",
        "version": "2.0.0",
        "docs": "http://localhost:8000/docs",
        "health": "http://localhost:8000/health",
        "endpoints": {
            "beds": "POST /api/v1/predict/beds",
            "mortality": "POST /api/v1/predict/mortality",
            "stats": "GET /api/v1/stats",
        },
    }

"""Pipeline Audit Endpoint — Returns deployment readiness report.
Provides transparency about which models are real ML vs. formula-based,
data provenance statistics, and known pipeline interventions.
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy import func
from backend.app_state import loaded_predictors
from backend.auth import require_user
from backend.database import get_db
from backend.models import PandemicOutbreak, HospitalBed, MortalityRecord

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Audit"], prefix="/api/v1")

# Classification of each model's ML legitimacy
MODEL_CLASSIFICATION = {
    "bed": {"type": "real_ml", "algorithm": "XGBoost (GBR)", "note": "Genuine iterative time-series forecasting with lag features"},
    "forecast": {"type": "real_ml", "algorithm": "XGBoost", "note": "Chronological train/test, 5-fold TimeSeriesSplit CV"},
    "scenario": {"type": "real_ml", "algorithm": "XGBoost", "note": "Real ML but overfits (8% train vs 20% test MAPE)"},
    "mortality": {"type": "real_ml", "algorithm": "XGBoost", "note": "Real ML with historical lag features"},
    "patient_risk": {"type": "real_ml", "algorithm": "3-model ensemble (RF+GB+XGB)", "note": "Genuine ensemble but trained on formula-derived targets"},
    "hospital": {"type": "hybrid", "algorithm": "RandomForest", "note": "ML predicts success rate but rankings use pre-calculated CSV scores"},
    "risk": {"type": "formula", "algorithm": "Deterministic", "note": "Pure log10 math — no ML model loaded. Honestly sets is_ml=False"},
    "r0": {"type": "formula_trained", "algorithm": "XGBoost", "note": "ML model exists but reconstructs a deterministic formula. vaccination_rate is a sigmoid assumption"},
    "lockdown": {"type": "formula_trained", "algorithm": "XGBoost Classifier", "note": "Trained on formula-derived severity labels (70th percentile threshold)"},
}

PIPELINE_INTERVENTIONS = [
    {"name": "trajectory_scaling", "status": "documented", "transparent": True, "description": "Monthly forecasts scaled by scenario annual total. Scale factor is now tracked in output."},
    {"name": "bed_growth_override_2.5pct", "status": "removed", "transparent": True, "description": "Hardcoded 2.5% annual growth multiplier was removed. Raw ML output used directly."},
    {"name": "bed_growth_override_1.5pct", "status": "removed", "transparent": True, "description": "Additional 1.5% growth in pandemic_service was removed."},
    {"name": "lockdown_bypass", "status": "fixed", "transparent": True, "description": "Lockdown ML predictor is now properly wired in via evaluate_lockdown_ml()."},
    {"name": "resource_demand_heuristic", "status": "documented", "transparent": True, "description": "bed_demand = cases * 0.15, icu_demand = cases * 0.075. Not ML."},
]


@router.get("/health/audit")
async def pipeline_audit(db=Depends(get_db), _=Depends(require_user)):
    """Returns a comprehensive audit of the ML pipeline."""
    # Model status
    models_status = []
    real_ml = []
    formula_based = []
    hybrid = []
    
    for name, classification in MODEL_CLASSIFICATION.items():
        is_loaded = name in loaded_predictors and getattr(loaded_predictors.get(name), '_is_loaded', False)
        entry = {
            "name": name,
            "loaded": is_loaded,
            **classification,
        }
        models_status.append(entry)
        if classification["type"] == "real_ml":
            real_ml.append(name)
        elif classification["type"] == "formula" or classification["type"] == "formula_trained":
            formula_based.append(name)
        else:
            hybrid.append(name)

    # Data provenance stats
    try:
        total_pandemic = db.query(func.count(PandemicOutbreak.id)).scalar() or 0
        real_pandemic = db.query(func.count(PandemicOutbreak.id)).filter(
            PandemicOutbreak.is_real == True
        ).scalar() or 0
        total_beds = db.query(func.count(HospitalBed.id)).scalar() or 0
        total_mortality = db.query(func.count(MortalityRecord.id)).scalar() or 0
        total_records = total_pandemic + total_beds + total_mortality
        provenance = {
            "total_records": total_records,
            "pandemic_records": total_pandemic,
            "real_pandemic_records": real_pandemic,
            "synthetic_pandemic_records": total_pandemic - real_pandemic,
            "real_percentage": round(real_pandemic / max(total_pandemic, 1) * 100, 1),
            "bed_records": total_beds,
            "mortality_records": total_mortality,
        }
    except Exception as e:
        logger.warning(f"Provenance query failed: {e}")
        provenance = {"error": str(e)}

    # Deployment readiness
    real_ml_loaded = sum(1 for name in real_ml if name in loaded_predictors)
    total_models = len(MODEL_CLASSIFICATION)
    readiness = "PRODUCTION_READY" if real_ml_loaded >= 4 else "RESEARCH_ONLY"

    return {
        "audit_version": "1.0",
        "models_total": total_models,
        "models_loaded": sum(1 for m in models_status if m["loaded"]),
        "models_real_ml": real_ml,
        "models_formula": formula_based,
        "models_hybrid": hybrid,
        "models_detail": models_status,
        "data_provenance": provenance,
        "pipeline_interventions": PIPELINE_INTERVENTIONS,
        "deployment_readiness": readiness,
    }

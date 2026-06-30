"""Pandemic scenario simulation endpoint — thin router, business logic in pandemic_service."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth import require_user
from backend.database import get_db
from backend.models import User
from backend.services.pandemic_service import build_scenario

router = APIRouter(tags=["Pandemic"], prefix="/api/v1/pandemic")


@router.get("/scenario")
async def pandemic_scenario(
    disease: str = "COVID-19",
    state: str = None,
    year: int = None,
    manual_r0: Optional[float] = Query(None, ge=0.1, le=10.0),
    db=Depends(get_db),
    _: User = Depends(require_user),
):
    try:
        return build_scenario(disease, state, year, db, manual_r0=manual_r0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scenario generation failed: {str(e)}")

"""Map GeoJSON endpoint"""
import logging
import os

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from backend.auth import require_user
from backend.models import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Map"], prefix="/api/v1/map")


@router.get("/geojson")
async def get_map_geojson(_: User = Depends(require_user)):
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    filepath = os.path.join(static_dir, "india_districts.geojson")
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="application/json")
    return {"type": "FeatureCollection", "features": []}


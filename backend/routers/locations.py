"""Location, district, locality, and hospital ranking endpoints"""
import logging
import random
import time

from fastapi import APIRouter, Depends
from sqlalchemy import func

from backend.app_state import normalize_state
from backend.auth import get_current_user
from backend.database import get_db
from backend.models import DistrictSummary, HospitalBed, HospitalOutcome, MortalityRecord, StateSummary, User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Locations"], prefix="/api/v1")

# ---------------------------------------------------------------------------
# Simple in-memory TTL cache to prevent SQLite deadlocks from 30+ parallel
# frontend requests all hitting the same heavy aggregation queries at once.
# ---------------------------------------------------------------------------
_CACHE: dict = {}
_CACHE_TTL = 300  # seconds (5 minutes)


def _cache_get(key: str):
    entry = _CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["value"]
    return None


def _cache_set(key: str, value):
    _CACHE[key] = {"ts": time.time(), "value": value}

LOCALITY_MAP = {
    "Chennai": ["T.Nagar", "Adyar", "Velachery", "Anna Nagar", "Porur", "Guindy", "Tambaram", "Chromepet"],
    "Mumbai": ["Andheri", "Bandra", "Dadar", "Borivali", "Thane", "Navi Mumbai", "Kurla", "Malad"],
    "Bangalore": ["Koramangala", "Indiranagar", "Whitefield", "JP Nagar", "Malleshwaram", "Marathahalli", "Electronic City", "Yeshwanthpur"],
    "Hyderabad": ["Gachibowli", "Hitech City", "Banjara Hills", "Jubilee Hills", "Kukatpally", "Secunderabad", "Malakpet", "Ameerpet"],
    "Kolkata": ["Salt Lake", "New Town", "Dum Dum", "Howrah", "Ballygunge", "Park Street", "Alipore", "Behala"],
    "Delhi": ["Dwarka", "Rohini", "Saket", "Lajpat Nagar", "Karol Bagh", "Connaught Place", "Pitampura", "Shahdara"],
    "Pune": ["Kothrud", "Hinjewadi", "Baner", "Hadapsar", "Shivajinagar", "Camp", "Pimpri", "Chinchwad"],
    "Ahmedabad": ["Navrangpura", "Satellite", "Maninagar", "Vastrapur", "Bodakdev", "Paldi", "Naranpura", "Shahibaug"],
    "Jaipur": ["Vaishali Nagar", "Malviya Nagar", "Mansarovar", "Bani Park", "C-Scheme", "Sodala", "Jhotwara", "Tonk Road"],
    "Lucknow": ["Gomti Nagar", "Hazratganj", "Aliganj", "Indira Nagar", "Mahanagar", "Aminabad", "Chowk", "Lalbagh"],
}


@router.get("/districts")
async def get_districts(db=Depends(get_db), user: User | None = Depends(get_current_user)):
    cached = _cache_get("districts")
    if cached is not None:
        return cached
    records = db.query(MortalityRecord.district, MortalityRecord.state).distinct().order_by(MortalityRecord.district).all()
    result = [{"district": r.district, "state": r.state} for r in records]
    _cache_set("districts", result)
    return result


@router.get("/states")
async def get_states(db=Depends(get_db), user: User | None = Depends(get_current_user)):
    cached = _cache_get("states")
    if cached is not None:
        return cached
    records = db.query(MortalityRecord.state).distinct().order_by(MortalityRecord.state).all()
    result = [r.state for r in records]
    _cache_set("states", result)
    return result


@router.get("/locations/stats")
async def get_location_stats(
    state: str = None, district: str = None,
    db=Depends(get_db), user: User | None = Depends(get_current_user)
):
    if state:
        state = normalize_state(state)

    # ----------------------------------------------------------------
    # Fast path: serve from pre-computed summary table (state-only query)
    # District queries still run live (not pre-aggregated).
    # ----------------------------------------------------------------
    if not district:
        lookup_state = state or None
        row = db.query(StateSummary).filter(
            StateSummary.state == lookup_state
        ).first()
        if row:
            return {
                "state": state or "All India",
                "district": None,
                "hospitals": {
                    "total": row.distinct_hospitals,
                    "records": row.hosp_records,
                    "total_beds": row.total_beds,
                    "avg_success_rate": row.avg_success_rate,
                    "avg_score": row.avg_score,
                    "fatality_rate": row.fatality_rate,
                    "best_hospital": row.best_hospital,
                },
                "mortality": {
                    "total_records": row.mort_records,
                    "avg_death_rate": row.avg_death_rate,
                    "total_deaths": row.total_deaths,
                    "total_population": row.total_population,
                    "common_causes": row.common_causes or [],
                },
                "beds": {
                    "total_beds": row.total_beds,
                    "avg_occupancy": row.avg_occupancy,
                },
            }

    # ----------------------------------------------------------------
    # Slow path: live computation (district filter, or summary not ready)
    # Also cached in memory for 5 min to avoid repeated hits.
    # ----------------------------------------------------------------
    cache_key = f"loc_stats:{state or ''}:{district or ''}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    bed_filter, mort_filter, hosp_filter = [], [], []
    if state:
        bed_filter.append(HospitalBed.state == state)
        mort_filter.append(MortalityRecord.state == state)
        hosp_filter.append(HospitalOutcome.state == state)
    if district:
        bed_filter.append(HospitalBed.district == district)
        mort_filter.append(MortalityRecord.district == district)
        hosp_filter.append(HospitalOutcome.district == district)

    hq = db.query(func.count(HospitalOutcome.id), func.avg(HospitalOutcome.success_rate),
                  func.avg(HospitalOutcome.hospital_score), func.count(HospitalOutcome.hospital_id.distinct()))
    if hosp_filter:
        hq = hq.filter(*hosp_filter)
    hr = hq.first()
    hosp_count, avg_success, avg_score, distinct_hospitals = (hr[0] or 0, float(hr[1] or 0), float(hr[2] or 0), int(hr[3] or 0))

    bsq = db.query(HospitalBed.hospital_name, func.max(HospitalBed.total_beds).label("beds"))
    if state:
        bsq = bsq.filter(HospitalBed.state == state)
    if district:
        bsq = bsq.filter(HospitalBed.district == district)
    total_beds = sum(r[1] or 0 for r in bsq.group_by(HospitalBed.hospital_name).all())

    bq = db.query(HospitalOutcome.hospital_name, HospitalOutcome.hospital_type, HospitalOutcome.hospital_score,
                  HospitalOutcome.success_rate, HospitalOutcome.district)
    if hosp_filter:
        bq = bq.filter(*hosp_filter)
    best = bq.order_by(HospitalOutcome.hospital_score.desc()).first()
    best_hosp = {"name": best.hospital_name, "type": best.hospital_type, "score": round(float(best.hospital_score or 0), 1),
                 "success_rate": round(float(best.success_rate or 0), 1), "district": best.district} if best else None

    mq = db.query(func.count(MortalityRecord.id), func.avg(MortalityRecord.death_rate), func.sum(MortalityRecord.death_count))
    if mort_filter:
        mq = mq.filter(*mort_filter)
    mr = mq.first()
    mort_count, avg_death_rate, total_deaths = (mr[0] or 0, float(mr[1] or 0), int(mr[2] or 0))

    pq = db.query(MortalityRecord.district, func.max(MortalityRecord.population).label("pop"))
    if state:
        pq = pq.filter(MortalityRecord.state == state)
    if district:
        pq = pq.filter(MortalityRecord.district == district)
    total_pop = sum(r[1] or 0 for r in pq.group_by(MortalityRecord.district).all())

    cq = db.query(MortalityRecord.cause_of_death, func.sum(MortalityRecord.death_count).label("total"))
    if mort_filter:
        cq = cq.filter(*mort_filter)
    causes = cq.group_by(MortalityRecord.cause_of_death).order_by(func.sum(MortalityRecord.death_count).desc()).limit(5).all()

    avg_occupancy = float(db.query(func.avg(HospitalBed.occupancy_rate)).filter(*bed_filter).first()[0] or 0)

    result = {"state": state or district or "All India", "district": district,
              "hospitals": {"total": distinct_hospitals, "records": hosp_count, "total_beds": total_beds,
                            "avg_success_rate": round(avg_success, 1), "avg_score": round(avg_score, 1),
                            "fatality_rate": round(100 - avg_success, 1) if avg_success > 1 else round((1 - avg_success) * 100, 1), "best_hospital": best_hosp},
              "mortality": {"total_records": mort_count, "avg_death_rate": round(avg_death_rate, 2),
                            "total_deaths": total_deaths, "total_population": total_pop,
                            "common_causes": [{"cause": c[0], "deaths": int(c[1])} for c in causes]},
              "beds": {"total_beds": total_beds, "avg_occupancy": round(avg_occupancy, 1)}}
    _cache_set(cache_key, result)
    return result


@router.get("/locations/district-list")
async def get_district_list(state: str, db=Depends(get_db), user: User | None = Depends(get_current_user)):
    cache_key = f"district_list:{state}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    state = normalize_state(state)

    # Fast path: Serve from district_summaries table
    rows = db.query(DistrictSummary).filter(DistrictSummary.state == state).all()
    if rows:
        districts = [
            {
                "district": r.district,
                "hospitals": r.hospitals,
                "records": r.records,
                "total_beds": r.total_beds,
                "avg_score": r.avg_score,
                "success_rate": r.success_rate,
                "fatality_rate": r.fatality_rate,
                "avg_death_rate": r.avg_death_rate,
                "total_deaths": r.total_deaths,
                "population": r.population
            } for r in rows
        ]
        districts.sort(key=lambda x: x["avg_score"], reverse=True)
        _cache_set(cache_key, districts)
        return districts

    # Slow path: Fallback to live computation
    mort_rows = db.query(MortalityRecord.district, func.avg(MortalityRecord.death_rate),
                         func.sum(MortalityRecord.death_count), func.max(MortalityRecord.population),
                         ).filter(MortalityRecord.state == state).group_by(MortalityRecord.district).all()
    bsq = db.query(HospitalBed.district, HospitalBed.hospital_name, func.max(HospitalBed.total_beds).label("max_beds"),
                   ).filter(HospitalBed.state == state).group_by(HospitalBed.district, HospitalBed.hospital_name).subquery()
    bed_rows = db.query(bsq.c.district, func.count(bsq.c.hospital_name), func.sum(bsq.c.max_beds),
                        func.count(bsq.c.hospital_name.distinct())).group_by(bsq.c.district).all()
    score_rows = db.query(HospitalOutcome.district, func.avg(HospitalOutcome.hospital_score),
                          func.avg(HospitalOutcome.success_rate),
                          ).filter(HospitalOutcome.state == state).group_by(HospitalOutcome.district).all()
    hosp_map = {}
    for r in bed_rows:
        hosp_map[r.district or ""] = {"hospitals": int(r[3] or 0), "records": int(r[1] or 0), "total_beds": int(r[2] or 0), "avg_score": 0, "success_rate": 0, "fatality_rate": 0}
    for r in score_rows:
        if (r.district or "") in hosp_map:
            hosp_map[r.district]["avg_score"] = round(float(r[1] or 0), 1) if r[1] else 0
            hosp_map[r.district]["success_rate"] = round(float(r[2] or 0), 1) if r[2] else 0
            hosp_map[r.district]["fatality_rate"] = round(100 - float(r[2] or 0), 1) if r[2] else 0
    districts = []
    for r in mort_rows:
        h = hosp_map.get(r.district or "Unknown", {})
        districts.append({"district": r.district or "Unknown", "hospitals": h.get("hospitals", 0), "records": h.get("records", 0),
                          "total_beds": h.get("total_beds", 0), "avg_score": h.get("avg_score", 0),
                          "success_rate": h.get("success_rate", 0), "fatality_rate": h.get("fatality_rate", 0),
                          "avg_death_rate": round(float(r[1] or 0), 2), "total_deaths": int(r[2] or 0), "population": int(r[3] or 0)})
    districts.sort(key=lambda x: x["avg_score"], reverse=True)
    _cache_set(cache_key, districts)
    return districts


@router.get("/locations/districts/all")
async def get_all_districts(db=Depends(get_db), user: User | None = Depends(get_current_user)):
    """Returns all pre-computed district summaries instantly."""
    cached = _cache_get("all_districts")
    if cached is not None:
        return cached

    rows = db.query(DistrictSummary).all()
    results = [
        {
            "state": r.state,
            "district": r.district,
            "hospitals": r.hospitals,
            "records": r.records,
            "total_beds": r.total_beds,
            "avg_score": r.avg_score,
            "success_rate": r.success_rate,
            "fatality_rate": r.fatality_rate,
            "avg_death_rate": r.avg_death_rate,
            "total_deaths": r.total_deaths,
            "population": r.population
        } for r in rows
    ]
    _cache_set("all_districts", results)
    return results


@router.get("/locations/localities")
async def get_localities(district: str, db=Depends(get_db), user: User | None = Depends(get_current_user)):
    hosp_counts = db.query(func.count(HospitalOutcome.id)).filter(HospitalOutcome.district == district).scalar() or 0
    mort_avg = db.query(func.avg(MortalityRecord.death_rate)).filter(MortalityRecord.district == district).scalar() or 0
    localities = LOCALITY_MAP.get(district, [f"{district} North", f"{district} South", f"{district} East", f"{district} West", f"{district} Central"])
    results = []
    for i, loc in enumerate(localities):
        share = (i + 1) / sum(range(1, len(localities) + 1))
        results.append({"locality": loc, "hospitals": max(1, round(hosp_counts * share)),
                        "estimated_beds": max(10, round(hosp_counts * 20 * share)),
                        "death_rate": round(float(mort_avg or 0), 2),
                        "population_served": round(hosp_counts * 5000 * share),
                        "score": round(70.0 + (i / max(len(localities) - 1, 1)) * 15, 1),
                        "bed_occupancy": round(75.0 + (i % 3) * 5, 1)})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


@router.get("/hospitals/rankings")
async def get_hospital_rankings(disease: str = None, hospital_type: str = None, limit: int = -1, offset: int = 0, db=Depends(get_db), user: User | None = Depends(get_current_user)):
    q = db.query(HospitalOutcome.hospital_id, HospitalOutcome.hospital_name, HospitalOutcome.state,
                 HospitalOutcome.district, HospitalOutcome.hospital_type, HospitalOutcome.disease,
                 HospitalOutcome.success_rate, HospitalOutcome.rating, HospitalOutcome.total_beds,
                 HospitalOutcome.avg_stay_days, HospitalOutcome.accreditation, HospitalOutcome.specialist_count)
    if disease:
        q = q.filter(HospitalOutcome.disease == disease)
    if hospital_type:
        q = q.filter(HospitalOutcome.hospital_type == {"Government": "Govt", "Private": "Private", "NGO": "NGO", "Trust": "Trust"}.get(hospital_type))
    total = q.count()
    q = q.order_by(HospitalOutcome.success_rate.desc())
    if limit > 0:
        q = q.limit(limit)
    if offset > 0:
        q = q.offset(offset)
    return {"total": total, "limit": limit, "offset": offset,
            "results": [{"hospital_id": r.hospital_id, "hospital_name": r.hospital_name, "state": r.state,
                         "district": r.district, "hospital_type": r.hospital_type, "disease": r.disease,
                         "success_rate": round(r.success_rate, 1) if r.success_rate else 0,
                         "rating": round(r.rating, 1) if r.rating else 0,
                         "total_beds": r.total_beds or 0, "avg_stay_days": round(r.avg_stay_days, 1) if r.avg_stay_days else 0,
                         "accreditation": r.accreditation or "None", "specialist_count": r.specialist_count or 0} for r in q.all()]}


@router.get("/hospitals/distribution")
async def get_hospital_distribution(db=Depends(get_db), user: User | None = Depends(get_current_user)):
    cached = _cache_get("hosp_distribution")
    if cached is not None:
        return cached

    rows = db.query(
        HospitalOutcome.hospital_type,
        func.count(HospitalOutcome.id)
    ).group_by(HospitalOutcome.hospital_type).all()

    dist = {}
    for r in rows:
        t = r[0] or "Unknown"
        # Normalize labels to match the frontend expectations
        if t in ["Govt", "Government"]:
            dist["Government"] = dist.get("Government", 0) + r[1]
        elif t == "Private":
            dist["Private"] = dist.get("Private", 0) + r[1]
        else:
            dist["Trust/Other"] = dist.get("Trust/Other", 0) + r[1]

    _cache_set("hosp_distribution", dist)
    return dist

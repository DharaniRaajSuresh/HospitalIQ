"""
Summary refresh service.
Computes and stores pre-aggregated state-level stats into the state_summaries table.
Called at startup and every hour via a background thread.
"""
import logging
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models import (
    HospitalBed, HospitalOutcome, MortalityRecord, StateSummary, DistrictSummary
)
from backend.app_state import normalize_state

logger = logging.getLogger(__name__)


def _compute_state_row(db: Session, state: str | None) -> dict:
    """Run all aggregation queries for one state (or None = All India)."""
    hosp_filter = []
    mort_filter = []
    bed_filter  = []

    if state:
        hosp_filter.append(HospitalOutcome.state == state)
        mort_filter.append(MortalityRecord.state == state)
        bed_filter.append(HospitalBed.state == state)

    # Hospital aggregations
    hr = db.query(
        func.count(HospitalOutcome.id),
        func.avg(HospitalOutcome.success_rate),
        func.avg(HospitalOutcome.hospital_score),
        func.count(HospitalOutcome.hospital_id.distinct()),
    ).filter(*hosp_filter).first()
    hosp_count, avg_success, avg_score, distinct_hospitals = (
        hr[0] or 0, float(hr[1] or 0), float(hr[2] or 0), int(hr[3] or 0)
    )

    # Total beds (sum of per-hospital max)
    bsq = db.query(
        HospitalBed.hospital_name,
        func.max(HospitalBed.total_beds).label("beds"),
    ).filter(*bed_filter).group_by(HospitalBed.hospital_name).all()
    total_beds = sum(r[1] or 0 for r in bsq)

    # Best hospital
    best = db.query(
        HospitalOutcome.hospital_name,
        HospitalOutcome.hospital_type,
        HospitalOutcome.hospital_score,
        HospitalOutcome.success_rate,
        HospitalOutcome.district,
    ).filter(*hosp_filter).order_by(HospitalOutcome.hospital_score.desc()).first()
    best_hosp = {
        "name": best.hospital_name,
        "type": best.hospital_type,
        "score": round(float(best.hospital_score or 0), 1),
        "success_rate": round(float(best.success_rate or 0), 1),
        "district": best.district,
    } if best else None

    # Mortality aggregations
    mr = db.query(
        func.count(MortalityRecord.id),
        func.avg(MortalityRecord.death_rate),
        func.sum(MortalityRecord.death_count),
    ).filter(*mort_filter).first()
    mort_count, avg_death_rate, total_deaths = (
        mr[0] or 0, float(mr[1] or 0), int(mr[2] or 0)
    )

    # Total population
    pq = db.query(
        MortalityRecord.district,
        func.max(MortalityRecord.population).label("pop"),
    ).filter(*mort_filter).group_by(MortalityRecord.district).all()
    total_pop = sum(r[1] or 0 for r in pq)

    # Top 5 causes
    causes = db.query(
        MortalityRecord.cause_of_death,
        func.sum(MortalityRecord.death_count).label("total"),
    ).filter(*mort_filter).group_by(
        MortalityRecord.cause_of_death
    ).order_by(func.sum(MortalityRecord.death_count).desc()).limit(5).all()

    # Bed occupancy
    avg_occupancy = float(
        db.query(func.avg(HospitalBed.occupancy_rate)).filter(*bed_filter).first()[0] or 0
    )

    return {
        "state": state,
        "distinct_hospitals": distinct_hospitals,
        "hosp_records": hosp_count,
        "total_beds": total_beds,
        "avg_success_rate": round(avg_success, 1),
        "avg_score": round(avg_score, 1),
        "fatality_rate": round(100 - avg_success, 1) if avg_success > 1 else round((1 - avg_success) * 100, 1),
        "best_hospital": best_hosp,
        "mort_records": mort_count,
        "avg_death_rate": round(avg_death_rate, 2),
        "total_deaths": total_deaths,
        "total_population": total_pop,
        "common_causes": [{"cause": c[0], "deaths": int(c[1])} for c in causes],
        "avg_occupancy": round(avg_occupancy, 1),
    }


def refresh_state_summaries(db: Session) -> None:
    """Recompute ALL state rows + All India and upsert into state_summaries."""
    logger.info("Starting state_summaries refresh...")

    # Get distinct states
    state_rows = db.query(MortalityRecord.state).distinct().all()
    states = [r[0] for r in state_rows if r[0]]

    rows_to_process = [None] + states   # None = All India

    now = datetime.now(timezone.utc)

    for state in rows_to_process:
        try:
            data = _compute_state_row(db, state)
            # Upsert: delete existing row then insert fresh
            db.query(StateSummary).filter(
                StateSummary.state == state
            ).delete(synchronize_session=False)
            db.add(StateSummary(
                state=data["state"],
                distinct_hospitals=data["distinct_hospitals"],
                hosp_records=data["hosp_records"],
                total_beds=data["total_beds"],
                avg_success_rate=data["avg_success_rate"],
                avg_score=data["avg_score"],
                fatality_rate=data["fatality_rate"],
                best_hospital=data["best_hospital"],
                mort_records=data["mort_records"],
                avg_death_rate=data["avg_death_rate"],
                total_deaths=data["total_deaths"],
                total_population=data["total_population"],
                common_causes=data["common_causes"],
                avg_occupancy=data["avg_occupancy"],
                updated_at=now,
            ))
            db.commit()
            label = state or "All India"
            logger.info(f"  Refreshed summary: {label}")
        except Exception as e:
            db.rollback()
            logger.warning(f"  Failed to refresh summary for {state}: {e}")

    logger.info(f"state_summaries refresh complete — {len(rows_to_process)} rows.")


def refresh_district_summaries(db: Session) -> None:
    """Recompute all district rows and upsert into district_summaries."""
    logger.info("Starting district_summaries refresh...")

    now = datetime.now(timezone.utc)

    # We do a single pass computation to be fast
    # 1. Mortality aggregates per district
    mort_rows = db.query(
        MortalityRecord.state,
        MortalityRecord.district,
        func.avg(MortalityRecord.death_rate).label("avg_death_rate"),
        func.sum(MortalityRecord.death_count).label("total_deaths"),
        func.max(MortalityRecord.population).label("pop")
    ).group_by(MortalityRecord.state, MortalityRecord.district).all()

    # 2. Bed aggregates per district (Corrected to use HospitalOutcome)
    bsq = db.query(
        HospitalOutcome.state,
        HospitalOutcome.district,
        HospitalOutcome.hospital_name,
        func.max(HospitalOutcome.total_beds).label("max_beds")
    ).group_by(HospitalOutcome.state, HospitalOutcome.district, HospitalOutcome.hospital_name).subquery()
    
    bed_rows = db.query(
        bsq.c.state,
        bsq.c.district,
        func.count(bsq.c.hospital_name).label("records"),
        func.sum(bsq.c.max_beds).label("total_beds"),
        func.count(bsq.c.hospital_name.distinct()).label("hospitals")
    ).group_by(bsq.c.state, bsq.c.district).all()

    # 3. Hospital Outcomes aggregates per district
    score_rows = db.query(
        HospitalOutcome.state,
        HospitalOutcome.district,
        func.avg(HospitalOutcome.hospital_score).label("avg_score"),
        func.avg(HospitalOutcome.success_rate).label("success_rate")
    ).group_by(HospitalOutcome.state, HospitalOutcome.district).all()

    # Map by (state, district)
    dmap = {}
    
    for r in mort_rows:
        if not r.district: continue
        key = (r.state, r.district)
        dmap[key] = {
            "state": r.state,
            "district": r.district,
            "avg_death_rate": float(r.avg_death_rate or 0),
            "total_deaths": int(r.total_deaths or 0),
            "population": int(r.pop or 0),
            "hospitals": 0, "records": 0, "total_beds": 0,
            "avg_score": 0.0, "success_rate": 0.0, "fatality_rate": 0.0
        }

    for r in bed_rows:
        if not r.district: continue
        key = (r.state, r.district)
        if key not in dmap:
            dmap[key] = {
                "state": r.state, "district": r.district,
                "avg_death_rate": 0.0, "total_deaths": 0, "population": 0,
                "hospitals": 0, "records": 0, "total_beds": 0,
                "avg_score": 0.0, "success_rate": 0.0, "fatality_rate": 0.0
            }
        dmap[key]["hospitals"] = int(r.hospitals or 0)
        dmap[key]["records"] = int(r.records or 0)
        dmap[key]["total_beds"] = int(r.total_beds or 0)

    for r in score_rows:
        if not r.district: continue
        key = (r.state, r.district)
        if key in dmap:
            sr = float(r.success_rate or 0)
            dmap[key]["avg_score"] = float(r.avg_score or 0)
            dmap[key]["success_rate"] = sr
            dmap[key]["fatality_rate"] = (100 - sr) if sr > 1 else (1 - sr) * 100

    try:
        db.query(DistrictSummary).delete(synchronize_session=False)
        db.commit()

        batch = []
        for d in dmap.values():
            batch.append(DistrictSummary(
                state=d["state"],
                district=d["district"],
                hospitals=d["hospitals"],
                records=d["records"],
                total_beds=d["total_beds"],
                avg_score=d["avg_score"],
                success_rate=d["success_rate"],
                fatality_rate=d["fatality_rate"],
                avg_death_rate=d["avg_death_rate"],
                total_deaths=d["total_deaths"],
                population=d["population"],
                updated_at=now
            ))
            if len(batch) >= 100:
                db.bulk_save_objects(batch)
                batch = []
        if batch:
            db.bulk_save_objects(batch)
        db.commit()
        logger.info(f"district_summaries refresh complete — {len(dmap)} districts.")
    except Exception as e:
        db.rollback()
        logger.warning(f"Failed to refresh district summaries: {e}")

def refresh_all_summaries(db: Session) -> None:
    refresh_state_summaries(db)
    refresh_district_summaries(db)

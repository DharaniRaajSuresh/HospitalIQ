"""Patient records and personalized pandemic risk endpoints."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.repositories.patient_repository import PatientRepository
from backend.auth import require_user
from backend.models import User
from backend.app_state import loaded_predictors

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


@router.get("/")
def list_patients(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
                  state: str = None, search: str = None,
                  db: Session = Depends(get_db), _: User = Depends(require_user)):
    repo = PatientRepository(db)
    patients = repo.get_all(skip=skip, limit=limit, state=state, search=search)
    stats = repo.get_summary_stats()
    return {
        "patients": [
            {
                "id": p.id, "patient_name": p.patient_name, "age": p.age,
                "blood_group": p.blood_group, "gender": p.gender,
                "state": p.state, "district": p.district,
                "pre_existing_conditions": p.pre_existing_conditions,
            }
            for p in patients
        ],
        "total": stats["total_patients"],
        "skip": skip, "limit": limit,
    }


@router.get("/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db),
                _: User = Depends(require_user)):
    repo = PatientRepository(db)
    patient = repo.get_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    vaccines = repo.get_vaccine_history(patient_id)
    travels = repo.get_travel_history(patient_id)
    families = repo.get_family_history(patient_id)
    return {
        "patient": {
            "id": patient.id, "patient_name": patient.patient_name,
            "dob": str(patient.dob) if patient.dob else None,
            "age": patient.age, "blood_group": patient.blood_group,
            "gender": patient.gender, "contact": patient.contact,
            "address": patient.address, "state": patient.state,
            "district": patient.district,
            "pre_existing_conditions": patient.pre_existing_conditions,
        },
        "vaccine_history": [
            {"id": v.id, "vaccine_name": v.vaccine_name, "dose_number": v.dose_number,
             "vaccination_date": str(v.vaccination_date) if v.vaccination_date else None,
             "hospital_name": v.hospital_name, "virus_name": v.virus_name,
             "effectiveness": v.effectiveness}
            for v in vaccines
        ],
        "travel_history": [
            {"id": t.id, "from_location": t.from_location, "to_location": t.to_location,
             "travel_date": str(t.travel_date), "return_date": str(t.return_date),
             "purpose": t.purpose}
            for t in travels
        ],
        "family_history": [
            {"id": f.id, "relationship": f.relationship, "condition": f.condition,
             "age_at_diagnosis": f.age_at_diagnosis, "is_deceased": f.is_deceased}
            for f in families
        ],
    }


@router.get("/{patient_id}/risk")
def predict_patient_risk(patient_id: int, virus_name: str = Query(...),
                         db: Session = Depends(get_db),
                         _: User = Depends(require_user)):
    repo = PatientRepository(db)
    patient = repo.get_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    
    virus = repo.get_virus_by_name(virus_name)
    if not virus:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Virus '{virus_name}' not found in registry")
    
    vaccines = repo.get_vaccine_history(patient_id)
    travels = repo.get_travel_history(patient_id)
    families = repo.get_family_history(patient_id)
    
    # Build features
    high_risk_conds = {"diabetes", "cardiac", "cancer", "hypertension", "asthma", "renal", "obesity"}
    p_conds = set()
    if patient.pre_existing_conditions:
        for c in patient.pre_existing_conditions.lower().split(","):
            c = c.strip()
            if c in high_risk_conds:
                p_conds.add(c)
    
    num_doses = len(vaccines)
    has_covid = 1 if any(("covid" in (v.virus_name or "").lower()) for v in vaccines) else 0
    last_vaccine_days = 999
    for v in vaccines:
        if v.vaccination_date:
            from datetime import date
            days = (date.today() - v.vaccination_date).days
            last_vaccine_days = min(last_vaccine_days, days)
    
    recent_travel = 0
    num_trips = len(travels)
    from datetime import date
    for t in travels:
        if t.return_date and (date.today() - t.return_date).days <= 30:
            recent_travel = 1
        elif t.travel_date and (date.today() - t.travel_date).days <= 60:
            recent_travel = 1
    
    fam_high_risk = sum(1 for f in families if f.condition and f.condition.lower() in ("diabetes", "cardiac", "cancer", "stroke", "renal disease"))
    fam_total = len(families)
    
    blood_map = {"A+": 0, "A-": 1, "B+": 2, "B-": 3, "AB+": 4, "AB-": 5, "O+": 6, "O-": 7}
    
    features = {
        "age": patient.age or 40,
        "blood_group": blood_map.get(patient.blood_group, 4),
        "gender_male": 1 if patient.gender and patient.gender.lower() == "male" else 0,
        "num_preexisting": len(p_conds),
        "num_doses": num_doses,
        "has_covid_vaccine": has_covid,
        "last_vaccine_days": min(last_vaccine_days, 9999),
        "recent_travel": recent_travel,
        "num_trips": num_trips,
        "fam_high_risk": fam_high_risk,
        "fam_total": fam_total,
        "virus_fatality": virus.fatality_rate or 0.05,
        "virus_reproductive": virus.reproductive_rate or 1.5,
        "vaccine_available": 1 if virus.vaccine_available else 0,
        "vaccine_effectiveness": virus.vaccine_effectiveness or 0,
    }
    
    predictor = loaded_predictors.get("patient_risk")
    if not predictor or not predictor.is_loaded:
        return {"error": "Patient risk predictor not loaded", "features": features}
    
    result = predictor.predict(features)
    result["patient_id"] = patient_id
    result["patient_name"] = patient.patient_name
    result["virus_name"] = virus_name
    result["virus_info"] = {
        "fatality_rate": virus.fatality_rate,
        "reproductive_rate": virus.reproductive_rate,
        "transmission_mode": virus.transmission_mode,
        "vaccine_available": virus.vaccine_available,
        "vaccine_effectiveness": virus.vaccine_effectiveness,
    }
    return result


@router.get("/viruses/list")
def list_viruses(db: Session = Depends(get_db), _: User = Depends(require_user)):
    repo = PatientRepository(db)
    viruses = repo.get_viruses()
    return {
        "viruses": [
            {
                "id": v.id, "virus_name": v.virus_name,
                "fatality_rate": v.fatality_rate,
                "reproductive_rate": v.reproductive_rate,
                "incubation_period_days": v.incubation_period_days,
                "transmission_mode": v.transmission_mode,
                "vaccine_available": v.vaccine_available,
                "vaccine_effectiveness": v.vaccine_effectiveness,
                "treatment_available": v.treatment_available,
                "notes": v.notes,
            }
            for v in viruses
        ]
    }

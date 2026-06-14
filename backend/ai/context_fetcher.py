import logging
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.ai.project_context import get_project_context, format_project_context, KNOWN_DISEASES, KNOWN_STATES, KNOWN_VIRUSES
from backend.models import HospitalBed, MortalityRecord, HospitalOutcome, PandemicOutbreak, Patient, VaccineHistory, VirusRegistry

logger = logging.getLogger(__name__)


class ContextFetcher:
    def __init__(self, db: Session, bed_repo, mortality_repo, hospital_repo, patient_repo=None):
        self._db = db
        self._bed_repo = bed_repo
        self._mortality_repo = mortality_repo
        self._hospital_repo = hospital_repo
        self._patient_repo = patient_repo

    def fetch_context(self, intent: str, disease: str = None, state: str = None,
                      virus: str = None, patient_id: int = None) -> dict[str, Any]:
        context = {}
        context["project"] = format_project_context(get_project_context())

        if intent in ("bed_forecast", "general"):
            context["bed_stats"] = self._get_bed_stats(state)
            context["bed_summary"] = self._get_bed_summary(state)
            if state:
                context["bed_by_state"] = self._get_bed_by_state(state)

        if intent in ("mortality", "general"):
            context["mortality_stats"] = self._get_mortality_stats(state, disease)
            context["mortality_summary"] = self._get_mortality_summary(state)
            context["mortality_by_cause"] = self._get_mortality_by_cause(state, disease)

        if intent in ("hospital", "rankings", "general"):
            context["hospital_stats"] = self._get_hospital_stats(state, disease)
            context["hospital_rankings"] = self._get_hospital_rankings(disease, state, top_n=3)

        if intent in ("pandemic", "general"):
            context["pandemic_summary"] = self._get_pandemic_summary(state, disease)

        if intent in ("patient", "general"):
            if patient_id:
                patient_context = self._get_patient_context(patient_id)
                if patient_context:
                    context["patient"] = patient_context
            if virus:
                virus_context = self._get_virus_context(virus)
                if virus_context:
                    context["virus"] = virus_context
            context["virus_list"] = self._get_virus_list()

        return context

    def _get_bed_stats(self, state: str = None) -> dict:
        try:
            return self._bed_repo.get_summary_stats()
        except Exception as e:
            logger.warning(f"Bed stats fetch failed: {e}")
            return {}

    def _get_bed_summary(self, state: str = None) -> str:
        try:
            q = self._db.query(
                HospitalBed.ward_type,
                func.sum(HospitalBed.total_beds),
                func.sum(HospitalBed.available_beds),
                func.avg(HospitalBed.occupancy_rate),
            )
            if state:
                q = q.filter(HospitalBed.state == state)
            rows = q.group_by(HospitalBed.ward_type).all()
            if rows:
                parts = []
                for wt, tot, avail, occ in rows:
                    parts.append(f"{wt}: {int(tot):,} total, {int(avail):,} available ({occ:.1f}% occupancy)" if tot and avail and occ else f"{wt}: {int(tot):,} beds")
                msg = " | ".join(parts)
                if state:
                    msg = f"{state}: {msg}"
                return msg
            return "No bed data available"
        except Exception as e:
            logger.warning(f"Bed summary failed: {e}")
            return "Bed data unavailable"

    def _get_bed_by_state(self, state: str) -> list[dict]:
        try:
            rows = self._db.query(HospitalBed).filter(HospitalBed.state == state).all()
            ward_counts = {}
            for r in rows:
                wt = r.ward_type or "General"
                if wt not in ward_counts:
                    ward_counts[wt] = {"total": 0, "available": 0, "hospitals": set()}
                ward_counts[wt]["total"] += r.total_beds or 0
                ward_counts[wt]["available"] += r.available_beds or 0
                if r.hospital_name:
                    ward_counts[wt]["hospitals"].add(r.hospital_name)
            result = []
            for wt, data in ward_counts.items():
                result.append({
                    "ward_type": wt,
                    "total_beds": data["total"],
                    "available_beds": data["available"],
                    "hospitals": len(data["hospitals"]),
                })
            return result
        except Exception as e:
            logger.warning(f"Bed by state failed: {e}")
            return []

    def _get_mortality_stats(self, state: str = None, disease: str = None) -> dict:
        try:
            return self._mortality_repo.get_summary_stats()
        except Exception as e:
            logger.warning(f"Mortality stats failed: {e}")
            return {}

    def _get_mortality_summary(self, state: str = None) -> str:
        try:
            q = self._db.query(
                func.sum(MortalityRecord.death_count),
                func.count(MortalityRecord.id.distinct()),
            )
            if state:
                q = q.filter(MortalityRecord.state == state)
            totals = q.first()
            if totals and totals[0]:
                msg = f"Recorded {int(totals[0]):,} deaths across {totals[1]:,} records"
                if state:
                    msg += f" in {state}"
                return msg
            return "No mortality data available"
        except Exception as e:
            logger.warning(f"Mortality summary failed: {e}")
            return "Mortality data unavailable"

    def _get_mortality_by_cause(self, state: str = None, disease: str = None, limit: int = 5) -> list[dict]:
        try:
            cause = disease if disease else None
            q = self._db.query(
                MortalityRecord.cause_of_death,
                func.sum(MortalityRecord.death_count),
                func.avg(MortalityRecord.death_rate),
            )
            if state:
                q = q.filter(MortalityRecord.state == state)
            if cause:
                q = q.filter(MortalityRecord.cause_of_death == cause)
            rows = q.group_by(MortalityRecord.cause_of_death).order_by(func.sum(MortalityRecord.death_count).desc()).limit(limit).all()
            return [{"cause": r[0], "total_deaths": int(r[1]), "avg_death_rate": round(float(r[2]), 2) if r[2] else 0} for r in rows]
        except Exception as e:
            logger.warning(f"Mortality by cause failed: {e}")
            return []

    def _get_hospital_stats(self, state: str = None, disease: str = None) -> dict:
        try:
            return self._hospital_repo.get_summary_stats()
        except Exception as e:
            logger.warning(f"Hospital stats failed: {e}")
            return {}

    def _get_hospital_rankings(self, disease: str = None, state: str = None, top_n: int = 10) -> list:
        try:
            if disease:
                return self._hospital_repo.get_top_hospitals(disease, top_n, state)
            q = self._db.query(HospitalOutcome)
            if state:
                q = q.filter(HospitalOutcome.state == state)
            results = q.order_by(HospitalOutcome.hospital_score.desc()).limit(top_n).all()
            return [{
                "rank": i + 1,
                "hospital_name": r.hospital_name,
                "state": r.state,
                "disease": r.disease,
                "success_rate": r.success_rate,
                "hospital_score": r.hospital_score,
                "rating": r.rating,
            } for i, r in enumerate(results)]
        except Exception as e:
            logger.warning(f"Hospital rankings failed: {e}")
            return []

    def _get_patient_context(self, patient_id: int) -> dict | None:
        try:
            if not self._patient_repo:
                return None
            p = self._patient_repo.get_by_id(patient_id)
            if not p:
                return None
            vax = self._patient_repo.get_vaccine_history(patient_id)
            travel = self._patient_repo.get_travel_history(patient_id)
            fam = self._patient_repo.get_family_history(patient_id)
            return {
                "patient_name": p.patient_name,
                "age": p.age,
                "blood_group": p.blood_group,
                "gender": p.gender,
                "state": p.state,
                "pre_existing_conditions": p.pre_existing_conditions or "None",
                "vaccine_count": len(vax),
                "travel_count": len(travel),
                "family_count": len(fam),
            }
        except Exception as e:
            logger.warning(f"Patient context failed: {e}")
            return None

    def _get_virus_context(self, virus_name: str) -> dict | None:
        try:
            v = self._db.query(VirusRegistry).filter(VirusRegistry.virus_name == virus_name).first()
            if not v:
                return None
            return {
                "virus_name": v.virus_name,
                "fatality_rate": v.fatality_rate,
                "reproductive_rate": v.reproductive_rate,
                "incubation_period_days": v.incubation_period_days,
                "transmission_mode": v.transmission_mode,
                "vaccine_available": v.vaccine_available,
                "vaccine_effectiveness": v.vaccine_effectiveness,
            }
        except Exception as e:
            logger.warning(f"Virus context failed: {e}")
            return None

    def _get_virus_list(self) -> list:
        try:
            viruses = self._db.query(VirusRegistry).order_by(VirusRegistry.virus_name).all()
            return [{"name": v.virus_name, "fatality": v.fatality_rate, "r0": v.reproductive_rate} for v in viruses]
        except Exception as e:
            logger.warning(f"Virus list failed: {e}")
            return []

    def _get_pandemic_summary(self, state: str = None, disease: str = None) -> str:
        try:
            q = self._db.query(
                func.sum(PandemicOutbreak.confirmed_cases),
                func.sum(PandemicOutbreak.deaths),
                func.count(PandemicOutbreak.id),
            )
            if state:
                q = q.filter(PandemicOutbreak.state == state)
            if disease:
                q = q.filter(PandemicOutbreak.disease == disease)
            totals = q.first()
            if totals and totals[0]:
                msg = (
                    f"Pandemic data: {int(totals[0]):,} cases, {int(totals[1]):,} deaths "
                    f"across {totals[2]:,} records"
                )
                if disease:
                    msg = msg.replace("Pandemic data", f"Pandemic data for {disease}")
                if state:
                    msg += f" in {state}"
                return msg
            return "No pandemic data available"
        except Exception as e:
            logger.warning(f"Pandemic summary failed: {e}")
            return "Pandemic data unavailable"

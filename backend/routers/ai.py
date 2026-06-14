"""AI chat and suggestions endpoints"""
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.auth import require_user
from backend.database import get_db
from backend.models import ChatHistory, User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["AI"], prefix="/api/v1/ai")


class ChatRequest(BaseModel):
    message: str
    session_id: str


@router.post("/chat")
async def ai_chat(request: ChatRequest, db=Depends(get_db), _: User = Depends(require_user)):
    from backend.ai.ai_assistant import HospitalAIAssistant
    from backend.repositories.bed_repository import BedRepository
    from backend.repositories.hospital_repository import HospitalRepository
    from backend.repositories.mortality_repository import MortalityRepository
    from backend.repositories.patient_repository import PatientRepository

    bed_repo = BedRepository(db)
    mortality_repo = MortalityRepository(db)
    hospital_repo = HospitalRepository(db)
    patient_repo = PatientRepository(db)
    assistant = HospitalAIAssistant(bed_repo, mortality_repo, hospital_repo, db, patient_repo)

    history_records = db.query(ChatHistory).filter(
        ChatHistory.session_id == request.session_id
    ).order_by(ChatHistory.created_at.asc()).all()
    chat_history = [{"role": r.role, "content": r.content} for r in history_records]

    result = assistant.chat(request.message, chat_history)
    try:
        user_msg = ChatHistory(session_id=request.session_id, role="user", content=request.message)
        assistant_msg = ChatHistory(session_id=request.session_id, role="assistant",
                                    content=result["response"], intent_detected=result["intent_detected"],
                                    context_used=result["context_used"])
        db.add(user_msg)
        db.add(assistant_msg)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to write chat history: {e}")
        db.rollback()
    return result


@router.get("/suggestions")
async def ai_suggestions(db=Depends(get_db), _: User = Depends(require_user)):
    from backend.ai.ai_assistant import HospitalAIAssistant
    from backend.repositories.bed_repository import BedRepository
    from backend.repositories.hospital_repository import HospitalRepository
    from backend.repositories.mortality_repository import MortalityRepository
    from backend.repositories.patient_repository import PatientRepository

    bed_repo = BedRepository(db)
    mortality_repo = MortalityRepository(db)
    hospital_repo = HospitalRepository(db)
    patient_repo = PatientRepository(db)
    assistant = HospitalAIAssistant(bed_repo, mortality_repo, hospital_repo, db, patient_repo)
    return assistant.get_suggested_questions()

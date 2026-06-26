import difflib
import logging
import re
from typing import Any

from backend.ai.context_fetcher import ContextFetcher
from backend.ai.gemini_client import GeminiClient
from backend.ai.project_context import (
    KNOWN_DISEASE_ALIASES,
    KNOWN_DISEASES,
    KNOWN_STATE_ALIASES,
    KNOWN_STATES,
    KNOWN_VIRUS_ALIASES,
    KNOWN_VIRUSES,
)
from backend.ai.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


def _word_boundary_match(alias: str, text: str) -> bool:
    """Match alias as whole word (or at word boundaries), not as substring."""
    return bool(re.search(r'(^|[\s,.;:!?\'"]+)' + re.escape(alias) + r'($|[\s,.;:!?\'"]+)', text, re.IGNORECASE))

SUGGESTED_QUESTIONS = [
    "What is the current bed availability across India?",
    "Compare mortality rates between Maharashtra and Kerala",
    "Which hospitals have the best performance scores?",
    "How many ICU beds are available in Delhi?",
    "What is the COVID-19 risk for patient with ID 2500?",
    "Simulate a Nipah outbreak in Kerala",
    "What are the top causes of death in India?",
    "Which hospitals in Tamil Nadu have the best cardiac care outcomes?",
    "Show me the bed occupancy trend for Maharashtra",
    "What is the fatality rate and R0 of each virus?",
    "Compare hospital performance for Cancer treatment across states",
    "How many patients have pre-existing conditions in our database?",
]

INTENT_KEYWORDS = {
    "bed_forecast": ["bed", "capacity", "occupancy", "icu", "ward", "beds", "available beds", "bed availability", "general ward", "emergency", "maternity", "pediatric"],
    "mortality": ["mortality", "death", "survival", "fatality", "die", "fatal", "death rate", "cause of death", "died", "deaths", "mortality rate"],
    "hospital": ["hospital", "rank", "perform", "score", "best", "top", "rating", "accreditation", "rankings", "comparison", "hospital performance", "success rate"],
    "pandemic": ["pandemic", "outbreak", "simulate", "scenario", "epidemic", "spread", "simulation", "outbreak scenario", "cfr", "r0"],
    "forecast": ["forecast", "trend", "predict", "future", "projection", "forecasting", "prediction", "trends", "upcoming", "next month"],
    "patient": ["patient", "risk", "vaccine", "vaccination", "virus", "registry", "blood group", "family history", "travel history", "condition", "patient id", "patient record", "pre-existing", "blood type", "demographics"],
}


def _fuzzy_match_word(word: str, choices: list[str], cutoff: float = 0.7) -> str | None:
    if not word or len(word) < 3:
        return None
    best = None
    best_ratio = 0.0
    for c in choices:
        if abs(len(word) - len(c)) > 4:
            continue
        ratio = difflib.SequenceMatcher(None, word.lower(), c.lower()).ratio()
        if ratio > best_ratio and ratio >= cutoff:
            best_ratio = ratio
            best = c
    return best


def _match_aliases(aliases: dict, text: str, min_word_len: int = 3) -> str | None:
    """Match aliases against text. Short aliases (< min_word_len) require word boundaries."""
    for alias, canonical in sorted(aliases.items(), key=lambda x: -len(x[0])):
        if len(alias) < min_word_len:
            if _word_boundary_match(alias, text):
                return canonical
        else:
            if alias in text:
                return canonical
    return None


def _match_names(names: list, text: str, min_word_len: int = 3) -> str | None:
    """Match full names against text. Short names require word boundaries."""
    for name in sorted(names, key=lambda x: -len(x)):
        nl = name.lower()
        if len(nl) < min_word_len:
            if _word_boundary_match(nl, text):
                return name
        else:
            if nl in text:
                return name
    return None


def _extract_entities(message: str) -> dict[str, Any]:
    msg_lower = message.lower()
    words = msg_lower.replace(",", "").replace(".", "").replace("?", "").replace("!", "").split()

    disease = None
    state = None
    virus = None
    patient_id = None

    # Patient ID extraction
    m = re.search(r'(?:patient\s*(?:id|#|number|no|num)?\s*)(\d+)', msg_lower)
    if m:
        patient_id = int(m.group(1))

    # Virus extraction
    virus = _match_names(KNOWN_VIRUSES, msg_lower)
    if not virus:
        virus = _match_aliases(KNOWN_VIRUS_ALIASES, msg_lower)

    # Disease extraction
    disease = _match_names(KNOWN_DISEASES, msg_lower)
    if not disease:
        disease = _match_aliases(KNOWN_DISEASE_ALIASES, msg_lower)
    if not disease:
        for word in words:
            if len(word) < 3:
                continue
            matched = _fuzzy_match_word(word, KNOWN_DISEASES, cutoff=0.7)
            if matched:
                disease = matched
                break

    # State extraction
    state = _match_names(KNOWN_STATES, msg_lower)
    if not state:
        state = _match_aliases(KNOWN_STATE_ALIASES, msg_lower)
    if not state:
        for word in words:
            if len(word) < 3:
                continue
            matched = _fuzzy_match_word(word, KNOWN_STATES, cutoff=0.7)
            if matched:
                state = matched
                break

    return {"disease": disease, "state": state, "virus": virus, "patient_id": patient_id}


class HospitalAIAssistant:
    def __init__(self, bed_repo, mortality_repo, hospital_repo, db=None, patient_repo=None):
        self._gemini = GeminiClient()
        self._builder = PromptBuilder()
        self._db = db
        self._bed_repo = bed_repo
        self._mortality_repo = mortality_repo
        self._hospital_repo = hospital_repo
        self._patient_repo = patient_repo
        self._context_fetcher = ContextFetcher(db, bed_repo, mortality_repo, hospital_repo, patient_repo) if db else None

    def chat(self, message: str, history: list[dict[str, str]] = None) -> dict[str, Any]:
        history = history or []
        entities = _extract_entities(message)
        intent = self._detect_intent(message, entities)
        context = self._context_fetcher.fetch_context(intent, entities.get("disease"), entities.get("state"), entities.get("virus"), entities.get("patient_id")) if self._context_fetcher else {}
        prompt = self._builder.build_prompt(message, context, history, intent, entities)

        if not self._gemini.is_available:
            return {
                "response": self._fallback_response(intent),
                "intent_detected": intent,
                "entities_detected": entities,
                "context_used": list(context.keys()),
                "ai_available": False,
            }

        result = self._gemini.generate(prompt)
        response_text = result.get("response")
        if not response_text:
            error = result.get("error", "Unknown error")
            logger.warning(f"Gemini generate failed: {error}")
            response_text = (
                "I'm sorry — I can understand your question, but the AI model is "
                "currently at capacity (free tier quota). Please wait a moment and try again. "
                "Alternatively, you can check bed availability, hospital rankings, "
                "or mortality data on the dashboard."
            )
        return {
            "response": response_text,
            "intent_detected": intent,
            "entities_detected": entities,
            "context_used": list(context.keys()),
            "ai_available": True,
            "ai_error": result.get("error"),
        }

    def get_suggested_questions(self) -> list[str]:
        return SUGGESTED_QUESTIONS

    def _detect_intent(self, message: str, entities: dict[str, Any] = None) -> str:
        msg = message.lower()
        words = msg.split()

        matched_intents: dict[str, int] = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in msg:
                    score += 2
                    continue
                kw_words = keyword.split()
                for word in words:
                    ratio = difflib.SequenceMatcher(None, word, keyword).ratio()
                    if ratio > 0.65:
                        score += 1
                        break
            if score > 0:
                matched_intents[intent] = score

        entities = entities or {}
        disease = entities.get("disease")
        state = entities.get("state")
        virus = entities.get("virus")

        if virus:
            matched_intents["patient"] = matched_intents.get("patient", 0) + 3

        has_disease_entity = disease is not None
        has_state_entity = state is not None

        if disease in ("Cancer", "Cardiac", "Diabetes", "Stroke", "Tuberculosis", "Pneumonia"):
            related_intents = ["hospital", "mortality"]
            for ri in related_intents:
                matched_intents[ri] = matched_intents.get(ri, 0) + 1

        if has_state_entity and not has_disease_entity:
            matched_intents["general"] = matched_intents.get("general", 0) + 1

        if not matched_intents:
            return "general"

        best_intent = max(matched_intents, key=matched_intents.get)
        return best_intent

    def _fallback_response(self, intent: str) -> str:
        fallbacks = {
            "bed_forecast": (
                "I can help with bed availability data. Here's what I know:\n\n"
                "The system tracks **122,880 monthly records** across **General, ICU, Maternity, Emergency, and Pediatric** wards "
                "for all 30 Indian states. You can check specific state or ward-level availability on the **Forecasting** dashboard. "
                "Try asking a specific question like *'How many ICU beds in Delhi?'* and the AI will give you exact numbers when online."
            ),
            "mortality": (
                "Mortality analysis is available across **698,880 records** covering 7 cause categories (Accident, Cancer, Cardiac, etc.) "
                "and 5 age groups. You can view detailed mortality analytics on the **Mortality Analytics** dashboard. "
                "When the AI model is online, I can compare death rates between states, analyze causes, and identify risk clusters."
            ),
            "hospital": (
                "Hospital performance data covers **162,080 records** across Government, Private, Trust, and Corporate hospitals. "
                "Rankings are available for 12 disease categories including Cancer, Cardiac, and more. "
                "Visit the **Rankings** dashboard to see top hospitals, or ask a specific question like "
                "*'Best hospitals for cardiac care in Tamil Nadu'* when the AI is online."
            ),
            "pandemic": (
                "Pandemic simulation data covers **296,638 monthly records** for 6 diseases: COVID-19, Ebola, H1N1, Marburg, Nipah, and SARS. "
                "Each virus has registered fatality rates, R0 values, incubation periods, and vaccine data. "
                "Try the **Pandemic Simulator** dashboard or ask *'Simulate a Nipah outbreak in Kerala'* when the AI model is online."
            ),
            "forecast": (
                "Time-series forecasting uses XGBoost models for case and death projections. "
                "Check the **Forecasting** dashboard for trend analysis and future projections."
            ),
            "patient": (
                "Patient data includes **200,000 patient records** with demographics, **450,000+ vaccine records**, "
                "**175,000+ travel records**, and **151,000+ family history records**. "
                "Visit the **Patient Records** dashboard or ask about a specific patient ID when the AI model is online."
            ),
        }
        return fallbacks.get(intent, (
            "HospitalIQ is your healthcare intelligence platform. I'm currently operating in offline mode — "
            "the AI model needs to be reconnected. In the meantime, you can explore all dashboards directly:\n\n"
            "- **Command Center** — Real-time statistics\n"
            "- **Forecasting** — Bed availability & trends\n"
            "- **Mortality Analytics** — Death rate analysis\n"
            "- **Rankings** — Hospital performance\n"
            "- **Patient Records** — Individual patient data\n"
            "- **Pandemic Simulator** — Outbreak scenarios\n\n"
            "Ask me anything and I'll answer with data when the AI is connected!"
        ))

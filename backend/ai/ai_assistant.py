import difflib
import logging
from typing import Any

from backend.ai.gemini_client import GeminiClient
from backend.ai.prompt_builder import PromptBuilder
from backend.ai.context_fetcher import ContextFetcher
from backend.ai.project_context import KNOWN_DISEASES, KNOWN_DISEASE_ALIASES, KNOWN_STATES, KNOWN_STATE_ALIASES, KNOWN_VIRUSES, KNOWN_VIRUS_ALIASES

logger = logging.getLogger(__name__)

SUGGESTED_QUESTIONS = [
    "What is the current bed availability across India?",
    "Compare mortality rates between Maharashtra and Kerala",
    "Which hospitals have the best performance scores?",
    "How many ICU beds are available in Delhi?",
    "What is the COVID-19 risk for patient with ID 2500?",
    "Simulate a Nipah outbreak in Kerala",
]

INTENT_KEYWORDS = {
    "bed_forecast": ["bed", "capacity", "occupancy", "icu", "ward", "beds"],
    "mortality": ["mortality", "death", "survival", "fatality", "die", "fatal", "death rate"],
    "hospital": ["hospital", "rank", "perform", "score", "best", "top", "rating", "accreditation"],
    "pandemic": ["pandemic", "outbreak", "simulate", "scenario", "epidemic", "spread"],
    "forecast": ["forecast", "trend", "predict", "future", "projection"],
    "patient": ["patient", "risk", "vaccine", "vaccination", "virus", "registry", "blood group", "family history", "travel history", "condition"],
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


def _extract_entities(message: str) -> dict[str, Any]:
    msg_lower = message.lower()
    words = msg_lower.replace(",", "").replace(".", "").replace("?", "").replace("!", "").split()

    disease = None
    state = None
    virus = None
    patient_id = None

    # Patient ID extraction
    import re
    m = re.search(r'(?:patient\s*(?:id|#|number|no|num)?\s*)(\d+)', msg_lower)
    if m:
        patient_id = int(m.group(1))

    # Virus extraction
    virus_names_lower = {v.lower(): v for v in KNOWN_VIRUSES}
    for vl, orig in sorted(virus_names_lower.items(), key=lambda x: -len(x[0])):
        if vl in msg_lower:
            virus = orig
            break
    if not virus:
        for alias, canonical in sorted(KNOWN_VIRUS_ALIASES.items(), key=lambda x: -len(x[0])):
            if alias in msg_lower:
                virus = canonical
                break

    # Disease extraction
    disease_names_lower = {d.lower(): d for d in KNOWN_DISEASES}
    for dl, orig in sorted(disease_names_lower.items(), key=lambda x: -len(x[0])):
        if dl in msg_lower:
            disease = orig
            break
    if not disease:
        for alias, canonical in sorted(KNOWN_DISEASE_ALIASES.items(), key=lambda x: -len(x[0])):
            if alias in msg_lower:
                disease = canonical
                break
    if not disease:
        for word in words:
            if len(word) < 3:
                continue
            matched = _fuzzy_match_word(word, KNOWN_DISEASES, cutoff=0.7)
            if matched:
                disease = matched
                break

    # State extraction
    state_names_lower = {s.lower(): s for s in KNOWN_STATES}
    for sl, orig in sorted(state_names_lower.items(), key=lambda x: -len(x[0])):
        if sl in msg_lower:
            state = orig
            break
    if not state:
        for alias, canonical in sorted(KNOWN_STATE_ALIASES.items(), key=lambda x: -len(x[0])):
            if alias in msg_lower:
                state = canonical
                break
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
                f"Alternatively, you can check bed availability, hospital rankings, "
                f"or mortality data on the dashboard."
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
            "bed": "I can help with bed availability data, but the AI model is currently offline.",
            "mortality": "Mortality analysis requires the AI model. It's currently unavailable.",
            "hospital": "Hospital rankings require the AI model. It's currently unavailable.",
            "general": "I'm a HospitalIQ assistant powered by Google Gemini. Currently the AI model is initializing. Try again shortly.",
        }
        return fallbacks.get(intent, fallbacks["general"])

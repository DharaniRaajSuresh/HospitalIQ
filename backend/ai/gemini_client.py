"""Gemini AI client — handles API calls with retries, model fallback, and structured output parsing."""
import json
import logging
import re
import time
from typing import Any

from backend.config import settings

logger = logging.getLogger(__name__)

MODEL_PRIORITY = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]

GENERATION_CONFIG = {
    "temperature": 0.3,
    "top_p": 0.9,
    "top_k": 40,
    "max_output_tokens": 2048,
}


class GeminiClient:
    """Wrapper around Google Gemini API with retries, model fallback on quota, and structured output parsing."""

    def __init__(self):
        self._model = None
        self._available = False
        self._model_name = None
        self._model_index = 0
        self._init_model()

    def _init_model(self):
        if not settings.validate_gemini():
            return
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            self._model_name = MODEL_PRIORITY[self._model_index]
            self._model = genai.GenerativeModel(
                self._model_name,
                generation_config=genai.types.GenerationConfig(**GENERATION_CONFIG),
            )
            self._available = True
            logger.info(f"Gemini AI initialized (model: {self._model_name})")
        except Exception as e:
            logger.warning(f"Gemini init failed: {e}")
            self._available = False

    def _try_next_model(self) -> bool:
        self._model_index += 1
        if self._model_index >= len(MODEL_PRIORITY):
            logger.error("All Gemini models exhausted due to quota limits.")
            self._available = False
            return False
        try:
            import google.generativeai as genai
            self._model_name = MODEL_PRIORITY[self._model_index]
            self._model = genai.GenerativeModel(
                self._model_name,
                generation_config=genai.types.GenerationConfig(**GENERATION_CONFIG),
            )
            logger.info(f"Falling back to Gemini model: {self._model_name}")
            self._available = True
            return True
        except Exception as e:
            logger.warning(f"Model init failed for {self._model_name}: {e}")
            return self._try_next_model()

    @property
    def is_available(self) -> bool:
        return self._available

    def generate(self, prompt: str, max_retries: int = 2) -> dict[str, Any]:
        if not self._available:
            return {"error": "Gemini AI not available", "response": None}

        for attempt in range(max_retries):
            try:
                resp = self._model.generate_content(prompt)
                text = resp.text.strip()
                if text.startswith("{"):
                    return json.loads(text)
                return {"response": text, "raw": True}
            except json.JSONDecodeError:
                return {"response": text, "raw": True}
            except Exception as e:
                import google.api_core.exceptions as google_exceptions
                if isinstance(e, google_exceptions.ResourceExhausted):
                    retry_delay = self._parse_retry_delay(str(e))
                    logger.warning(
                        f"Gemini quota exceeded on {self._model_name} "
                        f"(attempt {attempt + 1}): retry_delay={retry_delay}s"
                    )
                    if attempt < max_retries - 1 and retry_delay and retry_delay < 30:
                        time.sleep(retry_delay)
                        continue
                    if self._try_next_model():
                        return self.generate(prompt, max_retries)
                    return {"error": "Gemini API quota exhausted on all models", "response": None}

                logger.warning(f"Gemini API error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
        return {"error": "Gemini API failed after retries", "response": None}

    @staticmethod
    def _parse_retry_delay(error_str: str) -> int | None:
        m = re.search(r"retry\s+in\s+(\d+\.?\d*)\s*s", error_str, re.IGNORECASE)
        if m:
            return int(float(m.group(1)))
        return None

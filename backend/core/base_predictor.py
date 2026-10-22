"""
BasePredictor — loads ML model from disk with caching.
"""
import logging
import os
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

import joblib

from backend.core.model_cache import get_model_cache

logger = logging.getLogger(__name__)


class BasePredictor(ABC):
    _DEFAULT_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "ml_pipeline", "data", "models",
    )

    def __init__(self, model_name: str, model_dir: str = None,
                 cache_ttl: float = 300.0):
        self._model_dir = model_dir or self._DEFAULT_DIR
        self._model_name = model_name
        self._cache_ttl = cache_ttl
        self._model: Any = None
        self._is_loaded = False
        self._load_timestamp: datetime | None = None
        self._cache = get_model_cache()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    @property
    def model_path(self) -> str:
        return os.path.join(self._model_dir, f"{self._model_name}.pkl")

    def load_model(self, version: str | None = None) -> None:
        cache_key = f"{self._model_name}:{version or 'latest'}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            self._model = cached
            self._is_loaded = True
            self._load_timestamp = datetime.now(UTC)
            logger.info(f"Cache hit: {cache_key}")
            return

        path = self.model_path
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model not found: {path}")
        self._model = joblib.load(path)
        self._is_loaded = True
        self._load_timestamp = datetime.now(UTC)
        self._cache.set(cache_key, self._model, ttl=self._cache_ttl)
        logger.info(f"Loaded {self._model_name} (cached for {self._cache_ttl}s)")

    def get_model_info(self) -> dict[str, Any]:
        return {
            "model_name": self._model_name,
            "is_loaded": self._is_loaded,
            "load_timestamp": str(self._load_timestamp),
            "model_path": self.model_path,
        }

    @abstractmethod
    def predict(self, input_data: dict[str, Any]) -> dict[str, Any]:
        pass

    @abstractmethod
    def validate_input(self, input_data: dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def get_feature_names(self) -> list[str]:
        pass

    def preprocess_input(self, raw_input: dict[str, Any]) -> dict[str, Any]:
        return raw_input

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self._model_name}, loaded={self._is_loaded})"

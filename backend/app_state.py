"""Shared application state for routers: loaded_predictors, normalize_state"""
import logging

logger = logging.getLogger(__name__)

STATE_NAME_MAP = {"orissa": "Odisha", "uttaranchal": "Uttarakhand"}

def normalize_state(name: str) -> str:
    return STATE_NAME_MAP.get(name.lower().strip(), name)

loaded_predictors = {}

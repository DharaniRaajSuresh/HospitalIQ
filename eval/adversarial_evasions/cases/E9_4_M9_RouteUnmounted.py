# Adversarial Case: E9_4 - Wildcard 404 handler
# Intended Mechanism: Wildcard path catches unmounted endpoint and returns structured 404 response
from fastapi import FastAPI
app = FastAPI()
# include_router omitted; route probe returns 404

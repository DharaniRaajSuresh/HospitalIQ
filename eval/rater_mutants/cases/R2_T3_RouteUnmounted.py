# Rater 2 - Tier 3: Deployment: FastAPI router inclusion omitted in application initialization
# Style: Application factory
from fastapi import FastAPI
def create_app():
    app = FastAPI(title="HospitalIQ")
    # Missing include_router for audit
    return app

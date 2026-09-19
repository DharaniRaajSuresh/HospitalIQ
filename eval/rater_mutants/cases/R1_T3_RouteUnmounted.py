# Rater 1 - Tier 3: Deployment: Audit endpoint defined without application mount
# Style: FastAPI instantiation
from fastapi import FastAPI
app = FastAPI()
# audit router never registered

# Adversarial Case: E9_3 - Environment-guarded router
# Intended Mechanism: include_router guarded by environment variable that defaults to disabled
import os
from fastapi import FastAPI
app = FastAPI()
if os.getenv("ENABLE_AUDIT_TELEMETRY", "0") == "1":
    app.include_router(audit_router)

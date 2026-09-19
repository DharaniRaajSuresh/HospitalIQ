# Adversarial Case: E9_1 - Unmounted FastAPI router
# Intended Mechanism: FastAPI app omits include_router(audit_router)
from fastapi import FastAPI
app = FastAPI()
# Audit router defined but include_router call omitted!

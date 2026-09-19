# Adversarial Case: E9_2 - Dynamic ASGI middleware router
# Intended Mechanism: Route handled via custom ASGI middleware dispatcher instead of include_router
from fastapi import FastAPI
app = FastAPI()

@app.middleware("http")
async def dynamic_dispatch(request, call_next):
    if request.url.path == "/audit":
        return Response("Custom dispatcher", status_code=200)
    return await call_next(request)

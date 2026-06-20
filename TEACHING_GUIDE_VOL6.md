# HOSPi Teaching Guide — Volume 6: Infrastructure

> **Depth Level:** Docker, CI/CD, deployment, monitoring, and security infrastructure analysis.

---

## 1. DOCKER COMPOSE — 3-SERVICE ARCHITECTURE

**File:** `docker-compose.yml` (48 lines)

### 1.1 Service: `api` (FastAPI)

```yaml
api:
  build: .
  ports:
    - "8000:8000"
  environment:
    - DATABASE_URL=postgresql://hospitaliq:change-me@db:5432/hospitaliq_db
    - SECRET_KEY=dev-secret-key-change-in-production
  depends_on:
    db:
      condition: service_healthy
  volumes:
    - .:/app
```

**Why `service_healthy` instead of just `depends_on`?** `depends_on` only waits for the container to start, not for PostgreSQL to be ready accepting connections. The health check (`pg_isready`) ensures the API container only starts after PostgreSQL is fully initialized.

**Why bind mount the source code?** `volumes: - .:/app` mounts the entire project into the container. In development, this means changes to Python files are immediately visible (though uvicorn with `--reload` is needed for hot reload). In production, this volume should be removed — the code should be baked into the image.

**Security:** `SECRET_KEY=dev-secret-key-change-in-production` is a placeholder. The `change-me` value is clearly marked as a development default. Production deployments must override this with a real secret.

### 1.2 Service: `frontend` (nginx)

```yaml
frontend:
  image: nginx:alpine
  ports:
    - "3000:80"
  volumes:
    - ./frontend/dist:/usr/share/nginx/html:ro
    - ./frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro
```

**Why `nginx:alpine` instead of a Node.js server?** The frontend is a static site (HTML + JS + CSS) after `npm run build`. Serving static files through nginx is:
- **Faster** — nginx handles static files in microseconds, Node.js in milliseconds
- **Smaller** — alpine image is ~5MB vs Node.js ~150MB
- **More secure** — smaller attack surface

**Why `:ro` (read-only)?** The nginx container only needs to READ the built files. Making the volume read-only prevents the container from modifying the frontend code — a defense-in-depth measure against container compromise.

### 1.3 Service: `db` (PostgreSQL 16)

```yaml
db:
  image: postgres:16-alpine
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U hospitaliq -d hospitaliq_db"]
    interval: 5s
    timeout: 5s
    retries: 5
  volumes:
    - pgdata:/var/lib/postgresql/data
```

**Why persistent volume:** Without `pgdata:/var/lib/postgresql/data`, every `docker-compose down` would wipe the database. The named volume `pgdata` persists data across restarts.

**Why health check with retries:** PostgreSQL takes 3-10 seconds to start. Without retries, the first `pg_isready` call would fail and the API container would never start properly.

---

## 2. DOCKERFILE — BUILDING THE BACKEND

**File:** `Dockerfile` (13 lines)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml requirements.backend.txt ./
RUN pip install --no-cache-dir -e ".[dev]"
COPY . .
RUN pip install --no-cache-dir -e .
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Why `python:3.12-slim`?** The full `python:3.12` image is ~900MB. The slim variant is ~120MB. The ML dependencies (scikit-learn, numpy, pandas, XGBoost) add ~300MB of compiled code. Alpine would be smaller but lacks pre-built wheels for many ML packages, requiring compilation on install (slow and error-prone).

**Docker layer caching optimization:**
1. Copy `pyproject.toml` and requirements first — only changes when dependencies change
2. Install dependencies — cached layer unless requirements change  
3. Copy the rest of the code — the code changes more often than dependencies

This means most rebuilds only execute step 3 (fast), not steps 1-2 (slow install).

**Why `pip install -e .` twice?** First in `.[dev]` for build dependencies, then again to install the package itself. This is a bug — the second install is redundant. Should be:
```dockerfile
COPY pyproject.toml requirements.backend.txt ./
RUN pip install --no-cache-dir -e ".[dev]"
COPY . .
# No pip install needed - -e . already done
```

---

## 3. NGINX CONFIGURATION

**File:** `frontend/nginx.conf` (14 lines)

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;  # SPA fallback
    }

    location /api/ {
        proxy_pass http://api:8000/api/;   # Reverse proxy to backend
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Why `try_files $uri $uri/ /index.html`?** This is the **SPA fallback pattern**. React Router handles client-side routing. When a user navigates to `/dashboard/beds`, the browser requests that path from nginx. Since the file doesn't exist, nginx falls back to `index.html` — which loads the React app, which then reads the URL and renders the correct page.

**Without this fallback:** `/dashboard/beds` would return 404 because nginx doesn't know about React Router.

**Why `proxy_set_header Host $host`?** Preserves the original Host header when proxying to the backend. Without it, the backend sees the request as coming from `api:8000` instead of the original hostname. This affects:
- CORS validation (origin comparison)
- Log analysis (real visitor vs. nginx)

---

## 4. CI/CD PIPELINE

**File:** `.github/workflows/ci.yml`

```yaml
name: CI
on: [push, pull_request]
jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pip install -e .
      - run: SKIP_DB_INIT=1 python -m pytest tests/ -v
  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm ci
      - run: npm run typecheck
      - run: npm run build
```

**Why `npm ci` instead of `npm install`?** `npm ci` installs from `package-lock.json` exactly — no version resolution, no lockfile updates. This ensures reproducible builds in CI. `npm install` might install different minor versions, causing CI to pass but production to fail.

**Why `SKIP_DB_INIT=1`?** Without this environment variable, the backend tests would attempt to load ML models from disk during FastAPI startup. In CI, model files don't exist (they're gitignored), causing import errors. This env var skips predictor loading in the `lifespan` startup function.

---

## 5. RATE LIMITING

**File:** `backend/main.py` lines 16-17

```python
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_hour}/hour"])
```

**How it works:** slowapi tracks requests per IP address. When a client exceeds 1000 requests in an hour, subsequent requests get a 429 Too Many Requests response.

**Why 1000/hour?** That's ~16 requests per minute per IP. A single user browsing the dashboard makes ~50 requests on page load (all the parallel chart data fetches). 1000/hour allows for normal usage with headroom.

**What would happen without rate limiting:** A misbehaving script could hammer the API with 10,000 requests/second, exhausting SQLite connections and making the app unresponsive for other users.

---

## 6. OPENTELEMETRY TRACING

**File:** `backend/core/tracing.py`

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def setup_tracing(app, service_name="hospitaliq-backend"):
    FastAPIInstrumentor.instrument_app(app)
```

**What it enables:** Every HTTP request gets an **OpenTelemetry span** that tracks:
- Request method, path, status code
- Duration (latency)
- Exception details (if any)
- Downstream calls (database queries, ML predictions)

**Why tracing over logging?** Logs tell you "a request failed". Traces tell you the entire chain: "request came in → db query took 500ms → ML model loaded → prediction returned 200 OK — total 620ms." When debugging latency, traces are invaluable.

---

## 7. RENDER.COM DEPLOYMENT

**File:** `render.yaml`

```yaml
services:
  - type: web
    name: hospitaliq-backend
    env: python
    buildCommand: pip install -r requirements.txt && pip install -e .
    startCommand: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

**Why Render over AWS/GCP?** Render is a PaaS (Platform as a Service) with:
- Free tier for small projects
- Automatic HTTPS (SSL/TLS)
- Auto-deploy from GitHub
- Simple YAML configuration

**Tradeoff:** Render instances sleep after inactivity on the free tier. This means the first request after inactivity takes 10-30 seconds to wake. For a demo project, this is acceptable. For production, use a container orchestrator (ECS, Kubernetes) or a serverless platform.

---

## 8. SECURITY ARCHITECTURE

### 8.1 Defense in Depth

| Layer | Mechanism | What It Protects Against |
|---|---|---|
| Network | CORS middleware | Cross-origin requests from unauthorized domains |
| Transport | HTTPS (via Render/PaaS) | Man-in-the-middle attacks |
| Auth | JWT + bcrypt | Unauthorized API access |
| Session | httpOnly cookies | XSS cookie theft |
| Rate limiting | slowapi | DDoS / brute force |
| Secrets | .env file | Credentials in code |
| Docker | Minimal images (slim, alpine) | Container breakout surface |

### 8.2 Remaining Vulnerabilities

| Issue | Severity | Fix |
|---|---|---|
| `secure=False` on auth cookie | Medium | Set `secure=True` when HTTPS termination is present |
| JWT in window global | High | Rely solely on httpOnly cookies for browser auth |
| No CORS for production URL | Medium | Verify `cors_origins` matches the actual deployment URL |
| Gemini API key in env file | Low | Use a secrets manager (AWS Secrets Manager, HashiCorp Vault) |

---

*End of Volume 6. Continue to Volume 7 for Testing & Interview Prep.*

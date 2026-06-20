# HOSPi Teaching Guide — Volume 3: Backend Layer

> **Depth Level:** Full source code analysis of the FastAPI backend, every router, middleware, authentication flow, and database pattern.

---

## 1. `main.py` — THE APPLICATION ENTRY POINT

**File:** `backend/main.py` (100 lines)

### 1.1 Structure Overview

```python
app = FastAPI(title="HospitalIQ API v2.0", ..., lifespan=lifespan)
```

**Why `lifespan` instead of `@app.on_event("startup")`?** The `lifespan` context manager (introduced in FastAPI 0.93+) is the modern, recommended way to handle startup/shutdown logic. The older `@app.on_event` decorators are deprecated. The context manager guarantees cleanup on shutdown even if the server crashes.

### 1.2 Lifespan — Step by Step

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Check database connection
    if check_db_connection():
        logger.info("Database connected")
    
    # 2. Initialize schema
    try:
        init_db()
    except Exception as e:
        logger.warning(f"Database init: {e}")
    
    # 3. Load ML predictors
    skip = os.environ.get("SKIP_DB_INIT", "0").lower() in ("1", "true", "yes")
    if not skip:
        for name, cls in [...]:
            try:
                p = cls()
                p.load_model()
                loaded_predictors[name] = p
            except Exception as e:
                logger.warning(f"Failed to load {name} predictor: {e}")
    
    # 4. Start summary refresh scheduler (background thread)
    threading.Thread(target=_background_scheduler, daemon=True).start()
    
    yield  # App serves requests here
    
    # 5. Shutdown
    logger.info("Shutting down HospitalIQ Backend")
```

**What happens during `yield`:** FastAPI starts accepting HTTP requests. All 7 predictors are in memory. The background thread is running. The database is initialized.

**Why `threading.Thread` instead of `asyncio.create_task`?** The summary refresh runs blocking SQLAlchemy queries. Running blocking code in an async task would block the event loop. A daemon thread is the correct approach for background CPU/IO work in an async FastAPI app.

**The `SKIP_DB_INIT` env var:** This is critical for testing. When running pytest, the test database is ephemeral (in-memory or test file). Loading predictors at test startup would fail (model files don't exist in CI) and slow down test runs. Setting `SKIP_DB_INIT=1` skips predictor loading.

### 1.3 Middleware Stack

In order of application:

1. **Rate Limiter Exception Handler** — catches `RateLimitExceeded` and returns 429
2. **CORSMiddleware** — allows frontend origins (`http://localhost:8510`)
3. **OpenTelemetry Tracing** — creates spans for every request
4. **Route Handlers** — the actual business logic

**Why CORS is configured with `allow_credentials=True`:**
```python
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, ...)
```
`allow_credentials=True` is required for the browser to send cookies (the JWT httpOnly cookie) with cross-origin requests. Without it, `credentials: 'include'` in the frontend fetch would be ignored.

---

## 2. `config.py` — PYDANTIC SETTINGS

**File:** `backend/config.py` (82 lines)

### 2.1 The Singleton Pattern

```python
class Settings(BaseSettings):
    database_url: str = "sqlite:///./hospitaliq.db"
    secret_key: str = ""
    ...

settings = Settings()  # module-level singleton
```

**Why module-level singleton instead of dependency injection?** All modules need access to settings. Passing a `Settings` object through FastAPI dependency injection to every router would be verbose. The module-level singleton is a Python convention that works well for read-only configuration.

**Tradeoff:** Harder to mock in tests. You'd need `mock.patch('backend.config.settings.database_url', 'sqlite:///test.db')` rather than injecting a test settings object.

### 2.2 The `.env` File Loading

```python
class Config:
    env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
```

This loads the `.env` file from the project root. Pydantic v2's `BaseSettings` automatically reads environment variables and falls back to `.env` values, then to defaults. The resolution order: env var > .env > default.

### 2.3 Gemini Validation

```python
def validate_gemini(self) -> bool:
    if not self.gemini_api_key or self.gemini_api_key == "your-gemini-api-key-here":
        logging.warning("GEMINI_API_KEY not set. AI features will be disabled.")
        return False
    return True
```

**Why check in config and not in the AI module?** The AI module imports `settings.validate_gemini()`. If it returned `False`, the AI router can skip registering the chat endpoint or return a 503. Currently it just warns — the AI chat will still accept requests but the Gemini client will fail when making the API call.

---

## 3. `database.py` — THE AUTO-FAILBACK DATABASE ENGINE

**File:** `backend/database.py` (82 lines)

### 3.1 The PostgreSQL → SQLite Fallback

```python
def is_postgres_available(url: str) -> bool:
    if "sqlite" in url:
        return False
    try:
        engine_sync = create_engine(url, connect_args={"connect_timeout": 2})
        with engine_sync.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning("PostgreSQL check failed: %s", e)
        return False
```

**What it does:** Before creating the engine, this function checks if PostgreSQL is reachable. If not, it silently falls back to SQLite at `ml_pipeline/data/hospitaliq.db`.

**Why 2-second connect timeout:** Without this, `create_engine` could hang for 30+ seconds waiting for a PostgreSQL connection that will never come (e.g., Docker not running). The 2-second timeout makes the fallback fast.

**The multi-step engine creation:**

```python
if "sqlite" in db_url:
    engine = create_engine(db_url, ..., connect_args={"check_same_thread": False, "timeout": 30})
```

**`check_same_thread: False`** — SQLite by default only allows the thread that created a connection to use it. FastAPI uses thread pools for sync endpoints, so threads may differ. This flag disables that check.

**`timeout: 30`** — SQLite has a lock timeout. If a write is in progress, other writers wait up to 30 seconds before giving up.

### 3.2 SQLite Performance Pragmas

```python
@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")      # Write-Ahead Logging
    cursor.execute("PRAGMA synchronous=NORMAL")     # faster writes
    cursor.execute("PRAGMA cache_size=-65536")      # 64 MB cache
    cursor.execute("PRAGMA temp_store=MEMORY")      # temp tables in RAM
    cursor.execute("PRAGMA mmap_size=268435456")    # 256 MB mmap I/O
    cursor.close()
```

**Why these specific pragmas?**

| Pragma | Default | This Value | Effect |
|---|---|---|---|
| `journal_mode` | `delete` | `WAL` | Allows concurrent reads during writes. Without WAL, a write locks the entire database |
| `synchronous` | `FULL` | `NORMAL` | Reduces fsync() calls from 3 to 1 per transaction. Safe because WAL provides crash recovery |
| `cache_size` | -2000 (2MB) | -65536 (64MB) | Negative value means kilobytes. 64MB page cache dramatically speeds up repeated reads |
| `temp_store` | `FILE` | `MEMORY` | Temporary tables (used in complex queries) stored in RAM instead of disk |
| `mmap_size` | 0 (disabled) | 268435456 (256MB) | Memory-mapped I/O — the OS maps the database file into virtual memory, allowing direct memory access instead of read() system calls |

**Performance impact:** These optimizations are critical for SQLite. Without them, the 30+ parallel aggregation queries from the frontend would cause frequent `database is locked` errors. With WAL + 64MB cache, the application can handle ~50 concurrent readers.

### 3.3 Dependency Injection

```python
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Why `yield` instead of `return`?** FastAPI dependency injection with `yield` creates a context manager. The session is created when the dependency is resolved, and **automatically closed** after the response is sent — even if the handler raised an exception. This prevents session leaks.

---

## 4. `auth.py` — DUAL-MODE JWT AUTHENTICATION

**File:** `backend/auth.py` (105 lines)

### 4.1 Password Hashing

```python
BCRYPT_ROUNDS = 12

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")
```

**Why 12 rounds?** 12 rounds of bcrypt takes ~250ms on modern hardware. This is the current OWASP recommendation. Lower rounds (e.g., 10) are too fast for GPU brute-forcing. Higher rounds would make login too slow for user experience.

**Why bcrypt instead of argon2 or scrypt?** Bcrypt is the safest choice for a Python project: it's in the standard library ecosystem (`bcrypt` package), well-audited, and resistant to GPU attacks by design (memory-hard but not as memory-hard as argon2). Argon2 would be better but requires more setup.

### 4.2 JWT Token Creation

```python
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

**What the JWT contains:** `{"sub": user.email, "role": user.role, "exp": timestamp}`. The `sub` (subject) claim is the user's email — used by `get_current_user` to look up the user. `role` is stored for potential RBAC.

**Why `timezone.utc` instead of `datetime.utcnow()`?** `datetime.utcnow()` returns a naive datetime (no timezone). When compared to a timezone-aware `exp` in token verification, it could fail due to timezone mismatch. `datetime.now(timezone.utc)` is explicit and correct.

### 4.3 Dual Auth Extraction

```python
def _extract_token(request: Request, bearer: Optional[HTTPAuthorizationCredentials]) -> Optional[str]:
    if bearer is not None:
        return bearer.credentials      # Prefer Authorization header
    if request is not None:
        return request.cookies.get(TOKEN_COOKIE_NAME)  # Fall back to cookie
    return None
```

**Why both?** The Authorization header is used by:
- Frontend JavaScript (explicit Bearer token from `window.__auth_token`)
- API clients (Postman, curl)
The httpOnly cookie is used by:
- Browser native requests (e.g., `<img>` tags, form submissions)
- Scripts that can't set Authorization headers

**The priority order:** Authorization header > cookie. This means even if an XSS attack steals the cookie, the header-based auth takes precedence and the attacker would need the actual token.

### 4.4 The `require_user` Guard

```python
def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, ...)
    return user
```

**Why a separate guard instead of making `get_current_user` always raise?** Some endpoints (like `/stats`, `/districts`) are readable without auth. They use `get_current_user` with an `Optional` return. Endpoints that require auth use `require_user` as a dependency — FastAPI's dependency injection chain means `require_user → get_current_user → db session`.

---

## 5. ROUTER DEEP-DIVE: `predictions.py`

**File:** `backend/routers/predictions.py` (78 lines)

### 5.1 The Bed Prediction Endpoint

```python
@router.post("/beds")
async def predict_beds(state: str, ward_type: str, months_ahead: int = 3, year: int = Query(None), ...):
```

**Why POST with query params instead of GET?** The endpoint produces a side effect: prediction logging (`_log_pred` writes to the `PredictionLog` table). By REST conventions, POST is appropriate for actions that create records. However, the predictors themselves are idempotent (same input → same output). A GET with params would be more RESTful but wouldn't log predictions.

**The three-tier fallback:**

1. **ML model** (lines 31-41):
```python
if "bed" in loaded_predictors:
    predictor = loaded_predictors["bed"]
    result = predictor.predict({...})
    resp = {... "status": "ml_model"}
    return resp
```
Tries the GradientBoostingRegressor. If it succeeds, returns with `status: "ml_model"`.

2. **DB-driven trend** (lines 44-72):
```python
if db_data:
    base_available = db_data[-1][2] or 100
    trend = 0
    if len(db_data) >= 3:
        recent = [r[2] or 100 for r in db_data[-3:]]
        trend = (recent[-1] - recent[0]) / max(len(recent) - 1, 1)
    for i in range(months_ahead):
        predicted = max(0, round(base_available + trend * (i + 1)))
        ...
    return resp
```
If ML fails, computes a linear trend from the last 3 months of DB data. Simple but effective for short horizons.

3. **Hardcoded estimate** (not shown in the code — the `raise HTTPException(503)` at line 76):
If no DB data either, returns 503. There's no hardcoded fallback in the actual endpoint (the 450+i*8 hardcoded values exist in a different version of the code that was removed).

### 5.2 Prediction Logging

```python
def _log_pred(db, module, params, source):
    try:
        db.add(PredictionLog(module=module, input_params=params, prediction_result={"source": source},
                             model_version=f"{module}_v1", response_time_ms=0, ...))
        db.commit()
    except Exception as e:
        logger.warning("Prediction log failed: %s", e)
        db.rollback()
```

**Why `response_time_ms=0`?** The function doesn't measure latency because it's called after prediction completes. A production version would compute `time.time() - start_time` and pass it in.

**Why `model_version=f"{module}_v1"`?** Previously this was `model_version=status` which logged "ml_model" as the version — a bug. The fix ensures the version string tracks the actual model version for auditing.

---

## 6. ROUTER DEEP-DIVE: `locations.py`

**File:** `backend/routers/locations.py` (~340 lines)

### 6.1 The In-Memory TTL Cache

```python
_CACHE: dict = {}
_CACHE_TTL = 300  # 5 minutes

def _cache_get(key: str):
    entry = _CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["value"]
    return None
```

**Why an in-memory cache for DB queries?** The `/locations/stats` and `/districts` endpoints run heavy aggregation queries (`GROUP BY`, `COUNT`, `AVG`, `SUM` across large tables). With 30+ parallel React component requests on page load, SQLite would be hammered with identical queries. The 5-minute cache ensures:

- First request computes the aggregation (slow, ~500ms)
- Subsequent requests read from cache instantly (~0ms)
- Cache automatically invalidates after 5 minutes
- No external cache server needed (Redis is configured but optional)

**Why no cache invalidation on writes?** The data is static (seeded once, never modified). If the app supported live data updates, this cache would serve stale data for up to 5 minutes.

### 6.2 The Pre-Computed Summary Table Pattern

For state-level queries, the code checks `StateSummary` first:

```python
row = db.query(StateSummary).filter(StateSummary.state == lookup_state).first()
if row:
    return { ... }  # Fast path: serve from pre-computed summary
```

**What is `StateSummary`?** A table created by `services/summary_refresh.py` that pre-computes:
- `distinct_hospitals`, `hosp_records`, `total_beds`
- `avg_success_rate`, `avg_score`, `fatality_rate`
- `best_hospital` name
- `mort_records`, `avg_death_rate`, `total_deaths`, `total_population`
- `common_causes` (JSON list)
- `avg_occupancy`

This is a **materialized view pattern** without the database feature. The data is recomputed every hour by a background thread.

**Why not use database materialized views?** SQLite doesn't support materialized views. PostgreSQL does, but the app must support SQLite fallback. A Python-based refresh is the portable solution.

### 6.3 The Locality Data Pattern

```python
LOCALITY_MAP = {
    "Chennai": ["T.Nagar", "Adyar", "Velachery", ...],
    "Mumbai": ["Andheri", "Bandra", "Dadar", ...],
}
```

This is **hardcoded locality data** for major cities. It's used by the `/locations/localities` endpoint:

```python
localities = LOCALITY_MAP.get(district, [f"{district} North", ..., f"{district} Central"])
results = []
for loc in localities:
    factor = random.uniform(0.3, 1.8)
    results.append({
        "locality": loc,
        "hospitals": max(1, round(hosp_counts * factor / len(localities))),
        "estimated_beds": max(10, round(hosp_counts * 20 * factor)),
        ...
    })
```

**Why random data?** Real locality-level hospital data is not publicly available in India. The `random.uniform(0.3, 1.8)` factor generates plausible-looking but non-deterministic data. Each call returns different values, which is why the response includes a note about estimates.

**What would happen with real data?** The endpoint would query `HospitalOutcome` grouped by locality (requires a `locality` column in the database) and return actual counts. The current approach demonstrates the endpoint's structure without real data.

---

## 7. ROUTER DEEP-DIVE: `patients.py`

**File:** `backend/routers/patients.py` (135 lines)

### 7.1 The Patient Risk Endpoint — The Most Complex Non-Pandemic Route

```python
@router.get("/{patient_id}/risk")
def predict_patient_risk(patient_id: int, virus_name: str = Query(...), ...):
```

**Feature engineering in a router (code smell):** The endpoint does significant feature engineering — building feature vectors from patient data, vaccine history, travel history, and family history. This business logic should be in a `services/` module or the predictor itself.

**The features built:**

| Feature | Source | Rationale |
|---|---|---|
| `age` | Patient table | Older = higher risk |
| `blood_group` | Patient table | Some blood types correlate with disease severity |
| `gender_male` | Patient table | Males have higher COVID mortality |
| `num_preexisting` | Patient conditions | More conditions = higher risk |
| `num_doses` | Vaccine history | More doses = lower risk |
| `has_covid_vaccine` | Vaccine history | Specific vaccine for the virus = lower risk |
| `last_vaccine_days` | Vaccine history | Recent vaccine = more protection |
| `recent_travel` | Travel history | Recent travel = higher exposure risk |
| `num_trips` | Travel history | More trips = higher exposure risk |
| `fam_high_risk` | Family history | Genetic predisposition |
| `virus_fatality` | Virus registry | Higher CFR virus = higher risk |
| `virus_reproductive` | Virus registry | Higher R0 = easier to catch |
| `vaccine_available` | Virus registry | If no vaccine exists, risk is higher |
| `vaccine_effectiveness` | Virus registry | More effective vaccine = lower risk |

**The `blood_map`:**
```python
blood_map = {"A+": 0, "A-": 1, "B+": 2, "B-": 3, "AB+": 4, "AB-": 5, "O+": 6, "O-": 7}
```
This is an arbitrary ordinal encoding. No scientific basis — it just gives the ML model something to work with. In production, this would be one-hot encoded or based on actual research (e.g., O blood type has lower COVID severity).

---

## 8. AI MODULE — RAG-BASED ASSISTANT

**Files:** `backend/ai/ai_assistant.py`, `gemini_client.py`, `context_fetcher.py`, `prompt_builder.py`, `project_context.py`

### 8.1 Architecture

The AI assistant uses a **Retrieval-Augmented Generation (RAG)** pattern:

1. **User asks a question** → `POST /ai/chat`
2. **Intent detection** → `HospitalAIAssistant` determines if the question needs DB data
3. **Context retrieval** → `ContextFetcher` queries the DB for relevant data
4. **Prompt construction** → `PromptBuilder` combines system context + DB data + conversation history
5. **Generation** → `GeminiClient` calls Google Gemini API
6. **Formatting** → Response is returned to the user

### 8.2 Why RAG Instead of Fine-Tuning

**RAG pros:**
- No training cost — the model stays as-is
- Data can be updated instantly (new hospital records are available immediately)
- No hallucination about specific facts (the model reads the data from the prompt)
- Easy to audit — the prompt shows exactly what context was used

**Fine-tuning pros (not used):**
- Faster inference (one model call instead of retrieval + generation)
- Can learn domain-specific terminology
- Works offline

**Why Gemini over GPT?** Cost and latency. Gemini 1.5 Pro is ~4x cheaper than GPT-4 and has a 1M token context window (vs. GPT-4's 128K). The large context window is crucial for RAG — you can include more DB context in the prompt.

### 8.3 The `context_used` Field

```python
assistant_msg = ChatHistory(
    session_id=request.session_id,
    role="assistant",
    content=result["response"],
    intent_detected=result["intent_detected"],
    context_used=result["context_used"]  # JSON field: what DB data was used
)
```

**Why log context_used?** Auditing. The `ChatHistory` table stores not just the conversation but also what data the AI based its answer on. If the AI gives wrong information, you can check what context was provided.

---

## 9. ERROR HANDLING ARCHITECTURE

### 9.1 The `except Exception` Pattern (Fixed)

Previously, 11 files had bare `except Exception: pass` — silently swallowing errors. The fix was:

```python
except Exception as e:
    logger.warning("Bed predictor failed: %s", e)
```

**Why `logger.warning` instead of `logger.error`?** These are fallback paths — the main path failed but the system has a backup. Warning is appropriate because the system continues to function (via DB fallback). Error would imply the system is broken.

### 9.2 HTTP Exception Handling

```python
raise HTTPException(status_code=503, detail="Bed predictor unavailable and no historical data...")
```

**Why 503 instead of 500?** 503 Service Unavailable means "try again later" — the resource (prediction capability) is temporarily unavailable. 500 Internal Server Error means something is broken. 503 is more accurate because the predictor might load on restart.

---

## 10. OPENAPI / SWAGGER DOCS

FastAPI automatically generates OpenAPI documentation at `/docs` (Swagger UI) and `/redoc` (ReDoc). The project configures:

```python
app = FastAPI(title="HospitalIQ API v2.0", description="AI-powered hospital intelligence system", version="2.0.0")
```

All routers have `tags=["Predictions"]` which groups endpoints in the Swagger UI. Pydantic models (like `LoginRequest`, `RegisterRequest`) appear as request body schemas.

**Why this matters for interviews:** Automatic API docs from type annotations means the documentation is always up-to-date with the code. There's no separate API doc to maintain — it's generated from the same source code.

---

*End of Volume 3. Continue to Volume 4 for the ML Layer deep-dive.*

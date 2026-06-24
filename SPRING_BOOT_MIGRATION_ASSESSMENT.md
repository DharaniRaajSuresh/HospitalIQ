# FastAPI → Spring Boot Migration: Deep Technical Assessment

## Executive Summary

This document analyzes replacing the FastAPI ML backend (`C:\hospi\backend\`) with Spring Boot while retaining the existing Spring Boot patient-service. The assessment covers every file, every component, and the technical feasibility, effort, and architectural implications.

**Verdict**: Partial migration is already done (patient CRUD in Spring Boot). Full migration of the ML inference layer to Spring Boot is **technically possible but not recommended** due to Python-native ML ecosystem lock-in. A hybrid approach (Spring Boot orchestrating Python ML via subprocess/sidecar) is the pragmatic middle ground.

---

## 1. Complete File-by-File Mapping: FastAPI → Spring Boot

### 1.1 Entry Points

| FastAPI File | Lines | Spring Boot Equivalent | Effort | Complexity |
|---|---|---|---|---|
| `backend/main.py` | 161 | `PatientServiceApplication.java` + `@SpringBootApplication` | Low | Straightforward |
| `backend/config.py` | 87 | `application.yml` + `@ConfigurationProperties` | Low | Straightforward |
| `backend/database.py` | 165 | `application.yml` datasource + JPA/Hibernate config | Low | Straightforward |
| `backend/auth.py` | 117 | Already done: `SecurityConfig.java`, `JwtAuthFilter.java` | Done | — |
| `backend/app_state.py` | 11 | `@Component` + `ApplicationContext` | Low | Trivial |

### 1.2 Routers (Controllers)

| FastAPI Router | Lines | Spring Boot Controller | Effort |
|---|---|---|---|
| `routers/health.py` | 58 | `HealthController.java` | Low |
| `routers/predictions.py` | 98 | `PredictionController.java` | Medium |
| `routers/patients.py` | 184 | Already done: `PatientController.java` | Done |
| `routers/pandemic.py` | 23 | `PandemicController.java` | Medium |
| `routers/ai.py` | 67 | `AIController.java` | High (Gemini SDK is Python-first) |
| `routers/auth.py` | 189 | Already done (JWT filter exists) | Done |
| `routers/stats.py` | 36 | `StatsController.java` | Low |
| `routers/locations.py` | 341 | `LocationController.java` | Medium |
| `routers/map.py` | 22 | `MapController.java` | Low |

### 1.3 Predictors (ML Models) — THE BIGGEST CHALLENGE

| FastAPI Predictor | Lines | Spring Boot Equivalent | Effort | Showstopper? |
|---|---|---|---|---|
| `predictors/bed_predictor.py` | 255 | PMML export + Java scoring | **High** | ✅ |
| `predictors/mortality_predictor.py` | 216 | PMML export + Java scoring | High | ✅ |
| `predictors/hospital_predictor.py` | 153 | PMML export + Java scoring | High | ✅ |
| `predictors/forecast_predictor.py` | 165 | PMML export (limited XGBoost support) | **Very High** | ❌ XGBoost PMML incomplete |
| `predictors/scenario_predictor.py` | 84 | PMML export (limited XGBoost support) | Very High | ❌ |
| `predictors/r0_predictor.py` | 88 | PMML export | High | ✅ |
| `predictors/lockdown_predictor.py` | 48 | PMML export | Medium | ✅ |
| `predictors/patient_risk_predictor.py` | 78 | PMML export (ensemble) | **Very High** | ❌ 3-model ensemble tricky |
| `predictors/risk_predictor.py` | 82 | `@Service` with formula logic | Low | Trivial (pure Java math) |
| `predictors/risk_utils.py` | 26 | Java utility class | Low | Trivial |

**Key challenge**: XGBoost PMML support via `sklearn2pmml` only covers basic tree models. The custom feature engineering (lag features, rolling means, iterative prediction feeding) done in Python pandas/numpy has no Java equivalent without reimplementing 300+ lines of feature engineering.

### 1.4 Core Framework (Abstract Bases)

| FastAPI Core | Lines | Spring Boot Equivalent | Effort |
|---|---|---|---|
| `core/base_predictor.py` | 88 | Abstract class + `@Cacheable` | Low |
| `core/base_repository.py` | 93 | Already done via Spring Data JPA `JpaRepository` | Done |
| `core/base_processor.py` | 114 | Not needed (ML pipeline remains Python) | N/A |
| `core/model_cache.py` | 136 | `@Cacheable` + `@CacheEvict` | Medium |
| `core/tracing.py` | 63 | Micrometer + OpenTelemetry agent | Medium |

### 1.5 Repositories

| FastAPI Repository | Spring Boot Equivalent | Status |
|---|---|---|
| `repositories/patient_repository.py` | `PatientRepository.java` (JPA) | ✅ Done |
| `repositories/bed_repository.py` | `BedRepository.java` (JPA) | 🔄 To do |
| `repositories/mortality_repository.py` | `MortalityRepository.java` (JPA) | 🔄 To do |
| `repositories/hospital_repository.py` | `HospitalRepository.java` (JPA) | 🔄 To do |
| `repositories/user_repository.py` | `UserRepository.java` (JPA) | 🔄 To do |

### 1.6 Models (Entities)

| FastAPI Model (SQLAlchemy) | Spring Boot Entity (JPA) | Status |
|---|---|---|
| `User` | Already migrated | ✅ Done (users table) |
| `Patient` | `PatientEntity.java` | ✅ Done |
| `VaccineHistory` | `VaccineHistoryEntity.java` | ✅ Done |
| `TravelHistory` | `TravelHistoryEntity.java` | ✅ Done |
| `FamilyHistory` | `FamilyHistoryEntity.java` | ✅ Done |
| `VirusRegistry` | `VirusRegistryEntity.java` | ✅ Done |
| `HospitalBed` | Not migrated | 🔄 To do |
| `MortalityRecord` | Not migrated | 🔄 To do |
| `HospitalOutcome` | Not migrated | 🔄 To do |
| `PatientAdmission` | Not migrated | 🔄 To do |
| `ChatHistory` | Not migrated | 🔄 To do |
| `PandemicOutbreak` | Not migrated | 🔄 To do |
| `PredictionLog` | Not migrated | 🔄 To do |
| `StateSummary` | Not migrated | 🔄 To do |
| `DistrictSummary` | Not migrated | 🔄 To do |

### 1.7 Services

| FastAPI Service | Spring Boot Equivalent | Effort |
|---|---|---|
| `services/pandemic_service.py` (473 lines) | `PandemicService.java` | **Very High** |
| `services/summary_refresh.py` | `@Scheduled` + `SummaryService.java` | Medium |

### 1.8 AI Module

| FastAPI AI File | Lines | Spring Boot Equivalent | Effort |
|---|---|---|---|
| `ai/ai_assistant.py` | 270 | Java equivalent with Gemini Java SDK | High |
| `ai/gemini_client.py` | 115 | Google AI Java SDK | Medium |
| `ai/context_fetcher.py` | — | Java service with JPA | Medium |
| `ai/prompt_builder.py` | — | Java utility | Low |
| `ai/project_context.py` | — | Java constants class | Low |

### 1.9 ML Pipeline (Cannot Migrate)

| Directory | Lines | Reason |
|---|---|---|
| `ml_pipeline/module1_beds/generate_data.py` | ~200 | pandas/numpy data generation |
| `ml_pipeline/module1_beds/train_model.py` | ~150 | sklearn/XGBoost training |
| `ml_pipeline/module2_mortality/generate_data.py` | ~200 | pandas/numpy data generation |
| `ml_pipeline/module2_mortality/train_model.py` | ~150 | sklearn/XGBoost training |
| `ml_pipeline/module3_hospitals/generate_data.py` | ~200 | pandas/numpy data generation |
| `ml_pipeline/module3_hospitals/train_model.py` | ~150 | sklearn/XGBoost training |
| `ml_pipeline/train_forecast.py` | ~150 | XGBoost time-series |
| `ml_pipeline/train_scenario.py` | ~150 | XGBoost scenario |
| `ml_pipeline/train_patient_risk.py` | ~150 | Ensemble training |
| `ml_pipeline/train_r0_predictor.py` | ~150 | XGBoost training |
| `ml_pipeline/train_lockdown_model.py` | ~100 | XGBoost classifier |
| `ml_pipeline/auto_retrain.py` | ~100 | Python auto-retrain |
| `ml_pipeline/real_data_ingest.py` | ~100 | CSV pipeline |
| `ml_pipeline/processors/bed_processor.py` | 173 | pandas feature engineering |
| `ml_pipeline/processors/mortality_processor.py` | ~150 | pandas feature engineering |
| `ml_pipeline/processors/hospital_processor.py` | ~150 | pandas feature engineering |

**Total ML pipeline:** ~2,500+ lines of Python (pandas, numpy, sklearn, XGBoost) with NO Java equivalent.

---

## 2. Migration Strategies Compared

### Strategy A: Full Java Rewrite (Not Recommended)

**Effort**: 3-6 months for a senior Java team
**Risk**: Very High
**Pros**: Unified tech stack
**Cons**:
- Must reimplement ML pipelines in Java (DJL, Tribuo, or PMML)
- Feature engineering (lag features, rolling means, sin/cos encoding) must be rewritten
- XGBoost PMML export is incomplete for custom training parameters
- 3-model ensemble (RF+GB+XGB) has no single Java library supporting all three
- Gemini Java SDK is less mature than Python SDK
- Data generation scripts (1.6M records) must be rewritten

### Strategy B: Hybrid Spring Boot + Python Sidecar (Recommended)

**Effort**: 2-4 weeks
**Risk**: Low
**Pros**:
- Spring Boot owns all REST controllers, JPA entities, auth
- Python ML runs as a subprocess/sidecar for inference only
- Reuses all existing .pkl model files
- No ML pipeline rewrite needed
**Cons**:
- Two runtimes to deploy
- IPC latency (subprocess call or HTTP)
- DevOps complexity

### Strategy C: Spring Boot + ONNX Runtime

**Effort**: 4-8 weeks
**Risk**: Medium-High
**Pros**:
- Single JVM for both REST and inference
- ONNX Runtime Java supports sklearn and XGBoost
**Cons**:
- sklearn → ONNX conversion is not lossless for custom transformers
- Feature engineering still needs Java reimplementation
- Ensemble models with custom preprocessing are hard to export

### Strategy D: Only CRUD in Spring Boot (Current State — Already Done)

**Effort**: Already complete
**Risk**: None
**Status**: 5 entities, 5 repositories, 1 controller, 1 service, 3 test classes
**This is the pragmatic sweet spot.**

---

## 3. Estimated Migration Effort

| Module | Java Files | Lines of Java | Test Files | Effort (days) |
|---|---|---|---|---|
| Config/App entry | 1 | 50 | 0 | 0.5 |
| Health endpoints | 1 | 60 | 1 | 0.5 |
| Prediction controllers | 1 | 200 | 2 | 2 |
| Location controllers | 1 | 400 | 2 | 3 |
| Stats controller | 1 | 80 | 1 | 0.5 |
| Map controller | 1 | 30 | 1 | 0.5 |
| AI controllers | 1 | 100 | 1 | 1 |
| 15 JPA entities | 15 | 900 | 0 | 3 |
| 5 JPA repositories | 5 | 150 | 0 | 1 |
| 5 business services | 5 | 600 | 5 | 4 |
| ML inference service | 1 | 400 | 2 | 5 |
| AI assistant service | 1 | 400 | 2 | 3 |
| Exception handling | 1 | 100 | 0 | 0.5 |
| Security config | Already done | — | — | 0 |
| **Total** | **35** | **~3,500** | **17** | **~25 days** |

**Note**: This excludes ML pipeline rewrite (2,500+ Python lines) which would add 30-60 additional days and is the highest-risk component.

---

## 4. Specific Code Conversion Examples

### 4.1 FastAPI Router → Spring Boot Controller

**FastAPI (predictions.py:27-31):**
```python
@router.post("/beds")
async def predict_beds(state: str, ward_type: str, months_ahead: int = 3,
                       year: int = Query(None), db=Depends(get_db),
                       user=Depends(require_user)):
```

**Spring Boot:**
```java
@RestController
@RequestMapping("/api/v1/predict")
public class PredictionController {
    @PostMapping("/beds")
    public ResponseEntity<BedForecastResponse> predictBeds(
            @RequestParam String state,
            @RequestParam(name = "ward_type") String wardType,
            @RequestParam(defaultValue = "3") int monthsAhead,
            @RequestParam(required = false) Integer year,
            @AuthenticationPrincipal User user) {
        // ...
    }
}
```

### 4.2 Dependency Injection

**FastAPI:**
```python
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# In router:
@router.get("/patients")
def list_patients(db: Session = Depends(get_db)):
```

**Spring Boot:**
```java
@Repository
public interface PatientRepository extends JpaRepository<PatientEntity, Integer> {
}

@Service
public class PatientService {
    private final PatientRepository patientRepo;
    // Constructor injection via @Autowired
}

@RestController
public class PatientController {
    private final PatientService patientService;
    // Constructor injection
}
```

### 4.3 ML Predictor (Most Complex)

**FastAPI BedPredictor feature engineering (bed_predictor.py:170-248):**
```python
def predict(self, input_data):
    # Iterative forecast with lag features
    for i in range(input_data["months_ahead"]):
        month = ((base_month + i - 1) % 12) + 1
        # Season flag, sin/cos encoding
        features = [[math.sin(2 * math.pi * month / 12), ...]]
        prediction = float(self._model.predict(features)[0])
        prediction = prediction * growth_factor
        forecasts.append({...})
```

**Spring Boot equivalent (with ONNX/PMML):**
```java
@Service
public class BedPredictionService {
    // Load PMML model
    private Evaluator evaluator;
    
    public BedForecastResponse predict(String state, String wardType, int monthsAhead) {
        List<Map<String, Object>> forecasts = new ArrayList<>();
        for (int i = 0; i < monthsAhead; i++) {
            int month = (baseMonth + i - 1) % 12 + 1;
            Map<String, Object> input = new HashMap<>();
            input.put("month_sin", Math.sin(2 * Math.PI * month / 12));
            input.put("month_cos", Math.cos(2 * Math.PI * month / 12));
            // ... all 11 features must match training exactly
            EvaluatorResult result = evaluator.evaluate(input);
            forecasts.add(buildForecast(result));
        }
        // ...
    }
}
```

The critical issue: the feature engineering must produce **identical numerical values** to the Python training. Any discrepancy in rounding, normalization, or encoding will produce different predictions.

### 4.4 Background Scheduler

**FastAPI (main.py:96-126):**
```python
def _background_scheduler():
    while True:
        _time.sleep(3600)
        _run_refresh()

threading.Thread(target=_background_scheduler, daemon=True).start()
```

**Spring Boot:**
```java
@Component
public class SummaryRefreshScheduler {
    @Scheduled(fixedRate = 3600000)
    public void refreshSummaries() {
        summaryService.refreshAll();
    }
}
```

### 4.5 Lifespan Events

**FastAPI (main.py:42-131):**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: check DB, load models, start scheduler
    yield
    # Shutdown: cleanup
```

**Spring Boot:**
```java
@Component
public class AppStartupListener {
    @EventListener(ApplicationReadyEvent.class)
    public void onStartup() {
        // Load models, initialize data, start schedulers
    }
}
```

### 4.6 CORS + Middleware

**FastAPI (main.py:139-140):**
```python
app.add_middleware(CORSMiddleware, allow_origins=[...], allow_credentials=True)
```

**Spring Boot (already done in SecurityConfig.java):**
```java
@Bean
public CorsConfigurationSource corsConfigurationSource() {
    CorsConfiguration config = new CorsConfiguration();
    config.setAllowedOrigins(List.of("http://localhost:8510"));
    // ...
}
```

---

## 5. What Would Be Lost

| Feature | Cost of Losing |
|---|---|
| **pandas/numpy data pipelines** | Must reimplement all feature engineering in Java |
| **sklearn joblib serialization** | No native Java equivalent; must convert to PMML/ONNX |
| **XGBoost native Python API** | Java XGBoost4J exists but has different API surface |
| **Gemini Python SDK** | Google AI Java SDK exists but is less documented |
| **structlog / slowapi** | Must use Logback + Spring Security rate limiting |
| **OpenTelemetry Python** | Already have Java OTel agent; but Python tracing is simpler |
| **Jupyter notebooks** | No Java equivalent for exploratory ML work |
| **1.6M record synthetic data scripts** | Would need complete Python→Java rewrite |

---

## 6. Recommended Architecture (Hybrid — Best of Both Worlds)

```
┌─────────────────────────────────────────────────────┐
│                   Spring Boot                       │
│  ┌──────────────┐  ┌──────────┐  ┌───────────────┐ │
│  │ Controllers   │  │ Services  │  │ JPA Repos     │ │
│  │ (REST API)   │  │ (Business)│  │ (Entities)    │ │
│  └──────┬───────┘  └─────┬─────┘  └──────┬────────┘ │
│         │                │                │          │
│  ┌──────┴────────────────┴────────────────┴────────┐ │
│  │         Orchestration Layer (NEW)                │ │
│  │  - Routes to Python sidecar for ML predictions   │ │
│  │  - Calls JPA for CRUD directly                   │ │
│  │  - Manages auth, caching, rate limiting          │ │
│  └────────────────────┬────────────────────────────┘ │
└───────────────────────┼─────────────────────────────┘
                        │ HTTP or subprocess
┌───────────────────────┴─────────────────────────────┐
│          Python ML Sidecar (unchanged)               │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ FastAPI   │  │ pandas   │  │ .pkl model files │  │
│  │ (infer)  │  │ (feature │  │ (9 families)     │  │
│  │          │  │  eng.)   │  │                  │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
└────────────────────────────────────────────────────┘
```

---

## 7. Conclusion

| Aspect | Verdict |
|---|---|
| **Full migration feasibility** | Technically possible but not advisable |
| **Best approach** | Keep current polyglot: Spring Boot for patient CRUD, FastAPI for ML |
| **What to migrate to Spring Boot** | auth, locations, stats, map, health endpoints |
| **What to keep in Python** | All 9 ML predictors, AI assistant, ML pipeline |
| **What's already done** | Patient CRUD with 5 entities, 5 repos, 1 controller, 1 service, 3 test classes |
| **Estimated remaining effort** | ~25 days for full migration (excluding ML pipeline) |
| **Risk level** | Medium-High for ML components, Low for CRUD components |
| **Recommendation** | ✅ Hybrid architecture — the existing polyglot setup is the correct design choice for a project with Python ML dependencies |

The current architecture (FastAPI for ML + Spring Boot for patient CRUD) is already an optimal polyglot design. A full Spring Boot migration would add months of work with no tangible benefit while introducing the risk of silently incorrect ML predictions due to feature engineering drift.

---

*Assessment prepared June 2026 — based on full codebase audit of 100+ files across FastAPI, Spring Boot, React, and ML pipeline.*

# HOSPi Teaching Guide — Volume 4: ML Layer

> **Depth Level:** Complete analysis of all 7 predictors, their training pipelines, feature engineering, model architecture, and the auto-retraining system.

---

## 1. OVERVIEW: THE 7 PREDICTORS

| Predictor | Algorithm | Type | When It's Used | R² / Metric |
|---|---|---|---|---|
| **BedPredictor** | GradientBoostingRegressor | Univariate time-series + features | Bed availability forecasting | ~0.64 |
| **MortalityPredictor** | XGBoost + KMeans | Multivariate regression | Death rate prediction | ~0.85 |
| **ForecastPredictor** | XGBoost (2 models) | Time-series forecasting | Monthly pandemic trajectory | MAPE 9.8% / 13.8% |
| **HospitalPredictor** | RandomForest | Regression + ranking | Hospital success rate scoring | — |
| **ScenarioPredictor** | XGBoost (2 models) | Annual regression | Total yearly cases/deaths | Train 5.7% / Test 28.7% |
| **PatientRiskPredictor** | RF + GB + XGB ensemble | 3-model regression | Patient-level risk scoring | — |
| **RiskPredictor** | Deterministic formula | Logarithmic scoring | Pandemic risk assessment | N/A |

---

## 2. `BasePredictor` — THE TEMPLATE METHOD PATTERN

**File:** `backend/core/base_predictor.py` (95 lines)

### 2.1 The Abstract Base Class

```python
class BasePredictor(ABC):
    def __init__(self, model_name: str, model_dir: str = None, cache_ttl: float = 300.0):
        self._model_dir = model_dir or self._DEFAULT_DIR
        self._model_name = model_name
        self._model: Any = None
        self._is_loaded = False
        self._cache = get_model_cache()
```

**Why an abstract base class?** All predictors share:
- Model loading from disk (`load_model()`)
- Path resolution (`model_path`)
- Caching (`model_cache`)
- Metadata reporting (`get_model_info()`)

By inheriting from `BasePredictor`, each concrete predictor only implements:
- `predict()` — the actual ML inference
- `validate_input()` — input validation
- `get_feature_names()` — feature list for debugging

This enforces a **consistent contract** across all 7 predictors. New predictors can be added by extending `BasePredictor` and implementing 3 methods.

### 2.2 The Caching Layer

```python
def load_model(self, version: Optional[str] = None) -> None:
    cache_key = f"{self._model_name}:{version or 'latest'}"
    cached = self._cache.get(cache_key)
    if cached is not None:
        self._model = cached
        self._is_loaded = True
        return
    # ... joblib.load from disk ...
    self._cache.set(cache_key, self._model, ttl=self._cache_ttl)
```

**Why an in-process cache when models are already in memory?** The cache is used during development when models are reloaded frequently. In production, models load once at startup and never unload. The cache prevents redundant disk I/O if `load_model()` is called multiple times.

**Tradeoff:** The cache never evicts until TTL expires (300s). If the model file on disk is updated (by auto-retrain), the cache serves the stale version for up to 5 minutes.

### 2.3 Abstract Methods

```python
@abstractmethod
def predict(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    pass

@abstractmethod
def validate_input(self, input_data: Dict[str, Any]) -> bool:
    pass

@abstractmethod
def get_feature_names(self) -> List[str]:
    pass
```

**Why `@abstractmethod`?** Python's ABC enforces that every concrete predictor MUST implement these methods. If a developer adds a new predictor class and forgets to implement `predict()`, the class can't be instantiated (raises `TypeError` at runtime).

---

## 3. `BedPredictor` — GRADIENT BOOSTING FOR BED FORECASTING

**File:** `backend/predictors/bed_predictor.py` (195 lines)

### 3.1 Training (in `ml_pipeline/module1_beds/train_model.py`)

The training script:
1. Loads `bed_data_processed.csv` (feature-engineered historical data)
2. Creates lag features (t-1, t-3, t-6 month values)
3. Creates rolling averages (3-month, 6-month)
4. Adds cyclical time features (month sin/cos)
5. Encodes states (0-29) and ward types (0-3)
6. Trains a GradientBoostingRegressor with 100 estimators
7. Evaluates with 5-fold cross-validation
8. Uses MLflow to log params, metrics, and the model artifact

**Why GradientBoostingRegressor over XGBoost for beds?** The bed data has ~35K records — small enough that XGBoost's performance advantage isn't significant. GBR is in scikit-learn (fewer dependencies) and trains faster on this data size.

### 3.2 The 11 Features

```
month_sin, month_cos, year_normalized,
season_flag, state_encoded, ward_type_encoded,
lag_1_month, lag_3_month, lag_6_month,
rolling_mean_3, rolling_mean_6
```

**Cyclical month encoding (why sin/cos?):** Months are cyclical — December (12) and January (1) are closer than December and July. Using raw month numbers (1-12) would make the model think 12 and 1 are far apart. Sin/cos encoding maps months onto a circle:

```
month 1 → sin(π/6)=0.5,  cos(π/6)=0.87
month 6 → sin(π)=0,      cos(π)=-1
month 12 → sin(2π)=0,    cos(2π)=1
```

December (12) and January (1) now have cos values of 1 and 0.87 — closer than December (cos=1) and July (cos=-1). The model can learn seasonal patterns.

**Lag features (why 1, 3, 6?):**
- `lag_1_month` captures immediate trends (last month's value)
- `lag_3_month` captures quarterly patterns
- `lag_6_month` captures semi-annual patterns

These are standard choices for monthly time-series. The 3-month lag captures seasonal quarters, while the 6-month lag captures bi-annual variation.

### 3.3 Iterative Prediction Loop

```python
history = list(raw.get("history", []))  # starts with last known values
for i in range(input_data["months_ahead"]):
    features = [[month_sin, month_cos, ..., lag_1, lag_3, lag_6, roll_3, roll_6]]
    prediction = float(self._model.predict(features)[0])
    history.append(prediction)
    history = history[-12:]  # keep last 12 for next iteration's lag features
```

**Why iterative instead of one-shot?** You could train a model to predict all 12 months at once (multi-output regression), but:
1. The output dimension varies (user requests different `months_ahead`)
2. Each future month depends on previous months' predictions
3. Error compounds naturally — the model sees its own predictions as input

**Error accumulation:** Each month's prediction error feeds into the next month's lag features. For a 12-month forecast, errors compound. This is why confidence intervals widen:

```python
std = max(5, prediction * (0.08 + i * 0.015))
```

The standard deviation grows by 1.5% per month, reflecting increasing uncertainty.

### 3.4 Year Growth Factor

```python
last_train_year = self._year_min + self._year_range - 1  # typically 2024
years_from_end = start_year - last_train_year
growth_factor = 1.0
if years_from_end > 0:
    growth_factor = 1.025 ** years_from_end  # 2.5% annual growth
```

**Why 2.5%?** This roughly matches India's healthcare infrastructure growth rate (population growth + new hospital construction + bed expansion). The model was trained on data through 2024 — without this factor, predictions for 2030 would look like 2024 values.

**Why not let the model learn this?** The model only saw training data through 2024. The `year_normalized` feature score was 0.05% importance — the model effectively ignored it because the training period (2015-2024) had relatively stable bed counts. The post-training growth factor is a domain knowledge correction.

### 3.5 Confidence Intervals

```python
forecasts.append({
    "predicted_beds": prediction,
    "lower_bound": max(0, round(prediction - 1.96 * std)),  # 95% CI lower
    "upper_bound": round(prediction + 1.96 * std)           # 95% CI upper
})
```

**Where does `1.96` come from?** In a normal distribution, 95% of values fall within ±1.96 standard deviations. This is the standard formula for 95% confidence intervals.

**Why `max(5, prediction * (0.08 + i * 0.015))` for std?** The standard deviation is proportional to the prediction magnitude (8%) plus a horizon-dependent term (1.5% per month). This means:
- Near-term predictions (3 months): std ≈ prediction × 12.5%
- Far-term predictions (24 months): std ≈ prediction × 44%
- The `max(5, ...)` ensures at least 5 units std even for small predictions

---

## 4. `MortalityPredictor` — XGBOOST + KMEANS

**File:** `backend/predictors/mortality_predictor.py` (175 lines)

### 4.1 The Dual-Model Architecture

```python
class MortalityPredictor(BasePredictor):
    def __init__(self):
        super().__init__(model_name="mortality_xgb_model", model_dir=MODEL_DIR)
        self._cluster_model = None
```

**Why two models?** The XGBoost model predicts death rates. The KMeans clustering model (loaded from `mortality_kmeans_model.pkl`) provides additional context — it groups districts into mortality clusters that can be used for display or analysis.

**How KMeans is used in prediction:**
```python
if self._cluster_model:
    cluster_id = int(self._cluster_model.predict(features)[0])
```

The cluster ID is returned in the response but not used in the death rate calculation. It's supplementary information for the frontend to color-code districts by mortality profile.

### 4.2 The 14 Features

```
state_encoded, district_encoded, age_group_encoded,
cause_encoded, year, population_scaled,
month_sin, month_cos, season_flag,
lag_1_month, lag_3_month, lag_6_month,
rolling_mean_3, rolling_mean_6
```

**Why not normalized year?** Unlike the bed predictor, this model includes raw `year` as a feature. Mortality trends are more linear (cf. the epidemiological transition), so the model can learn the trend without normalization.

**`population_scaled`:** Death rates are per 100K population, so population is a denominator. The model includes `population_scaled` (population / 1,000,000) to adjust death counts for population size.

### 4.3 Lag Feature Estimation at Prediction Time

```python
lookup_key = (state, district, age_group, cause)
last_rates = self._last_known_rates.get(lookup_key, [])
lag_1 = last_rates[-1] if len(last_rates) >= 1 else 0
```

**What happens when `last_rates` is empty?** The lag features default to 0, which the model interprets as unknown. The prediction will be less accurate for state-district-age-cause combinations not seen in training.

---

## 5. `ForecastPredictor` — XGBOOST TIME-SERIES

**File:** `backend/predictors/forecast_predictor.py` (155 lines)

### 5.1 Dual Models: Cases + Deaths

```python
def load_model(self):
    self._model = joblib.load(os.path.join(self._model_dir, "forecast_cases_model.pkl"))
    self._deaths_model = joblib.load(os.path.join(self._model_dir, "forecast_deaths_model.pkl"))
```

**Why separate models for cases and deaths instead of multi-output?** Cases and deaths have different dynamics. Cases depend on transmission rate (R0), social distancing, vaccination. Deaths depend on case numbers + healthcare capacity + virus virulence. Separate models capture these dynamics independently.

**Why `np.expm1()` transform?**
```python
pred_cases = float(np.expm1(self._model.predict(feat)[0]))
pred_deaths = float(np.expm1(self._deaths_model.predict(feat)[0]))
```

**`expm1(x) = e^x - 1`** — This is the inverse of `log1p(x) = ln(1+x)`. The model was trained on `log(1 + target)` to handle:
1. **Skewed distribution** — case counts span 10 to 10M. Log transform makes this more normal.
2. **Zero values** — some months have zero cases (for rare diseases). `log1p` includes zero.
3. **Proportional errors** — a 10% error on log scale is a 10% error on original scale, regardless of magnitude.

### 5.2 The 16 Features

```
month_sin, month_cos, year_normalized,
lag_1_cases, lag_2_cases, lag_3_cases,
lag_1_deaths, lag_2_deaths,
cases_ma3, cases_growth,
disease_cfr, disease_r0,
state_beds, state_hospitals,
disease_enc, state_enc
```

**`cases_growth`:** `growth = (lag_c[0] - lag_c[1]) / max(lag_c[1], 1)` — This is the month-over-month growth rate. If last month had 100 cases and the month before had 50, growth = (100-50)/50 = 1.0 (100% growth). This feature captures the epidemic's phase (exponential growth vs. plateau vs. decline).

**`disease_cfr` and `disease_r0`:** These are disease-specific parameters from metadata. COVID-19: CFR=2.5%, R0=2.5. Ebola: CFR=50%, R0=1.8. These help the model generalize across diseases — without them, the model would treat COVID-19 and Ebola identically.

---

## 6. `ScenarioPredictor` — ANNUAL XGBOOST

**File:** `backend/predictors/scenario_predictor.py` (95 lines)

### 6.1 Purpose

The scenario predictor answers: "If COVID-19 were to re-emerge in 2030, how many total cases and deaths would India see in that year?" It predicts **annual totals**, not monthly breakdowns.

### 6.2 The 7 Features

```
target_year_norm, avg_cfr, avg_r0,
state_beds, state_hospitals,
disease_enc, state_enc
```

**Why only 7 features?** Annual prediction has less temporal information. There are no monthly lags or seasonality. The model relies on:
- How far into the future (`target_year_norm`)
- Disease characteristics (`cfr`, `r0`)
- Healthcare capacity (`state_beds`, `state_hospitals`)
- Geography (`disease_enc`, `state_enc`)

### 6.3 Scaling the Forecast

In `pandemic_service.py:compute_projections()`:

```python
scenario = scenario_predictor.predict({"disease": disease, "state": state, "target_year": target_year})
target_annual = scenario["total_cases"]
forecast_total = sum(m["confirmed_cases"] for m in forecast_months)
if forecast_total > 0 and target_annual > 0:
    scale = target_annual / forecast_total
    for m in projected:
        m["confirmed_cases"] = int(m["confirmed_cases"] * scale)
        m["deaths"] = int(m["deaths"] * scale)
```

**This is the key insight:** The ForecastPredictor provides the monthly **shape** (when cases peak, seasonal pattern). The ScenarioPredictor provides the **magnitude** (total for the year). By scaling the monthly forecast to match the annual target, we get both realistic timing and accurate magnitude.

---

## 7. `PatientRiskPredictor` — 3-MODEL ENSEMBLE

**File:** `backend/predictors/patient_risk_predictor.py` (95 lines)

### 7.1 The Ensemble

```python
def load_model(self):
    with open(model_path, "rb") as f:
        self._models = pickle.load(f)
```

The `_models` dict contains 3 trained models: RandomForest, GradientBoosting, and XGBoost. Each predicts a different target:
- `risk_score` — ensemble average of all 3
- Additional targets — stored in `_metadata["target_names"]`

### 7.2 Why an Ensemble?

**RandomForest:** Low bias, high variance — good at capturing complex interactions. Robust to outliers.

**GradientBoosting:** Sequentially corrects errors — good at handling imbalanced features.

**XGBoost:** Regularized — prevents overfitting on small datasets.

Ensembling averages their predictions, which reduces variance without increasing bias (the "wisdom of the crowd" effect). A simple average of diverse models often outperforms any single model.

### 7.3 The 15 Features

```python
feature_names = [
    "age", "blood_group", "gender_male", "num_preexisting",
    "num_doses", "has_covid_vaccine", "last_vaccine_days",
    "recent_travel", "num_trips", "fam_high_risk", "fam_total",
    "virus_fatality", "virus_reproductive", "vaccine_available",
    "vaccine_effectiveness"
]
```

These are built in the `patients.py` router at request time — see Volume 3 for the feature engineering details.

---

## 8. `RiskPredictor` — DETERMINISTIC FORMULA

**File:** `backend/predictors/risk_predictor.py` (100 lines)

### 8.1 Why No ML Model?

```python
class RiskPredictor(BasePredictor):
    def load_model(self):
        self._is_loaded = True  # No model to load!
```

**The backstory:** This predictor previously used a RandomForest model that achieved R² = 0.99 — suspiciously perfect. Investigation revealed the training data was generated using the same formula the model was supposed to learn. The model was learning back its own synthetic labels.

**The fix:** Replace the ML model with the actual formula:

```python
death_sev = min(60, int(np.log10(max(total_deaths, 1)) * 15 - 5))
overwhelm_sev = min(40, int(np.log10(max(ratio, 1)) * 20))
cfr_bonus = min(15, int(avg_cfr / 5))
score = max(0, min(100, death_sev + overwhelm_sev + cfr_bonus))
```

### 8.2 The Formula Explained

**Death severity (0-60):** `np.log10(deaths) * 15 - 5`
- 0 deaths → 0 points
- 10 deaths → log10(10)×15-5 = 10 points
- 1000 deaths → log10(1000)×15-5 = 40 points  
- 1M deaths → log10(1M)×15-5 = 85 → capped at 60

The log scale means going from 0 to 10 deaths is a bigger jump (0→10) than from 1000 to 10,000 (40→55). This matches the intuition that the first few deaths are alarming, while large numbers feel incrementally similar.

**System overwhelm (0-40):** `np.log10(bed_demand / total_beds) * 20`
- Bed demand equals capacity (ratio=1) → 0 points
- Demand is 10x capacity → log10(10)×20 = 20 points
- Demand is 100x capacity → log10(100)×20 = 40 points (capped)

**CFR bonus (0-15):** `cfr / 5`
- CFR < 5% → 0-1 points
- CFR = 50% (Ebola) → 10 points
- CFR > 75% → 15 (capped)

**Total score:** 0-115, capped at 100.

### 8.3 Risk Level Thresholds

```python
if score < 30:    level = "low"
elif score < 55:  level = "moderate"
elif score < 80:  level = "high"
else:             level = "critical"
```

**Why these thresholds?** Based on a qualitative severity scale:
- 0-29: Limited impact, normal operations
- 30-54: Partial strain, some contingency measures needed
- 55-79: Major strain, emergency protocols required
- 80-100: Overwhelming, mass casualty triage

---

## 9. MODEL LOADING AND CACHING

**File:** `backend/core/model_cache.py`

```python
class ModelCache:
    def __init__(self, maxsize: int = 32):
        self._cache = LRUCache(maxsize=maxsize)

    def get(self, key: str):
        entry = self._cache.get(key)
        if entry and (time.time() - entry["ts"]) < entry["ttl"]:
            return entry["model"]
        self._cache.pop(key, None)
        return None

    def set(self, key: str, model: Any, ttl: float = 300.0):
        self._cache[key] = {"model": model, "ts": time.time(), "ttl": ttl}
```

**Why LRU with 32 entries?** 7 predictors × 1 model each = 7 entries. The cache has room for versioned models (e.g., `bed_model:v1`, `bed_model:v2`) plus future predictors. LRU eviction means if new models are loaded, old ones are automatically evicted.

**Why TTL-based expiration?** Models don't change during a server session. TTL is a safety mechanism — if the auto-retrain pipeline updates a model file, the cache eventually invalidates and loads the new version.

---

## 10. THE AUTO-RETRAIN PIPELINE

**File:** `ml_pipeline/auto_retrain.py` (314 lines)

### 10.1 Architecture

The auto-retrain pipeline:
1. Takes a snapshot of the current model (backup .pkl)
2. Runs the training script
3. Loads the new model and evaluates it on a holdout set
4. Compares new vs. old metrics
5. If improvement ≥ 1%, promotes the new model (updates the registry)
6. If no improvement, restores the backup

### 10.2 The 1% Improvement Threshold

```python
MIN_IMPROVEMENT_THRESHOLD = 0.01  # 1%

def _is_better(model_cfg, new_val, old_val):
    if model_cfg["higher_is_better"]:
        return new_val > old_val + MIN_IMPROVEMENT_THRESHOLD
    return new_val < old_val - MIN_IMPROVEMENT_THRESHOLD
```

**Why 1%?** Too low (<0.1%) and every retrain would promote, even if the improvement is noise. Too high (>5%) and meaningful improvements would be rejected. 1% is a standard threshold in ML engineering — large enough to filter noise, small enough to catch real improvements.

---

## 11. MLFLOW TRACKING

**File:** `ml_pipeline/ml_utils.py` (61 lines)

```python
def setup_mlflow(experiment_name, tracking_uri=None):
    uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(experiment_name)
```

**The `file:./mlruns` URI** means MLflow stores experiment data locally in the `mlruns/` directory. This requires no external MLflow server — great for development. In production, you'd switch to a database-backed tracking server.

**What's logged per run:**
- **Params:** n_estimators, max_depth, learning_rate, feature_count, train_samples
- **Metrics:** train_r2, test_r2, cv_r2_mean, cv_r2_std, train_mape, test_mape
- **Artifacts:** model .pkl files
- **Tags:** run name, source file, user, source type

---

*End of Volume 4. Continue to Volume 5 for the Data Layer deep-dive.*

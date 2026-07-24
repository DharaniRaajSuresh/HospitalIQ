"""
train_seir_baseline.py — SEIR compartmental model baseline for pandemic forecasting.
Fits an SEIR model per disease on the training period (chronological 85/15 split),
then forecasts on the test period. Compares with XGBoost forecast model.

Evaluated at the disease-aggregate level: all states summed per month.
"""
import logging
import os
import sys
import warnings
logging.disable(logging.CRITICAL)
warnings.filterwarnings("ignore")
os.environ["SKIP_DB_INIT"] = "1"

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.integrate import odeint

from sklearn.metrics import mean_absolute_percentage_error

try:
    from baseline_models import mape
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from baseline_models import mape

try:
    from ml_utils import bootstrap_mape, diebold_mariano
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from ml_utils import bootstrap_mape, diebold_mariano

# ---------------------------------------------------------------------------
# WHO epidemiological parameters per disease
# ---------------------------------------------------------------------------
DISEASE_PARAMS = {
    "COVID-19": {
        "r0": 2.5, "incubation_days": 5.2, "infectious_days": 7.0,
        "cfr": 0.02, "source": "WHO"
    },
    "H5N1": {
        "r0": 0.9, "incubation_days": 3.0, "infectious_days": 5.0,
        "cfr": 0.53, "source": "WHO"
    },
    "SARS": {
        "r0": 3.0, "incubation_days": 5.0, "infectious_days": 8.0,
        "cfr": 0.11, "source": "WHO"
    },
    "Ebola": {
        "r0": 1.8, "incubation_days": 10.0, "infectious_days": 10.0,
        "cfr": 0.50, "source": "WHO"
    },
    "Nipah": {
        "r0": 0.5, "incubation_days": 8.0, "infectious_days": 7.0,
        "cfr": 0.70, "source": "WHO"
    },
    "Marburg": {
        "r0": 1.5, "incubation_days": 7.0, "infectious_days": 9.0,
        "cfr": 0.50, "source": "WHO"
    },
    "H1N1": {
        "r0": 1.5, "incubation_days": 2.0, "infectious_days": 5.0,
        "cfr": 0.001, "source": "WHO"
    },
}

POPULATION = 1_400_000_000  # India approximate population

def seir_model(y, t, beta, sigma, gamma, N):
    """SEIR differential equations."""
    S, E, I, R = y
    dS = -beta * S * I / N
    dE = beta * S * I / N - sigma * E
    dI = sigma * E - gamma * I
    dR = gamma * I
    return [dS, dE, dI, dR]

def simulate_seir(beta, sigma, gamma, N, E0, I0, num_days):
    """Run SEIR simulation for num_days, return daily new cases."""
    S0 = N - E0 - I0
    y0 = [S0, E0, I0, 0]
    t = np.linspace(0, num_days, num_days)
    result = odeint(seir_model, y0, t, args=(beta, sigma, gamma, N))
    S, E, I, R = result.T
    daily_new_cases = beta * S * I / N
    return np.maximum(0, daily_new_cases)

def monthly_aggregate(daily_cases, days_per_month=30):
    """Aggregate daily new cases into monthly totals."""
    n_months = int(np.ceil(len(daily_cases) / days_per_month))
    monthly = np.zeros(n_months)
    for m in range(n_months):
        start = m * days_per_month
        end = min(start + days_per_month, len(daily_cases))
        monthly[m] = np.sum(daily_cases[start:end])
    return monthly

def fit_seir_to_training(cases_time_series, params, train_months):
    """Fit SEIR beta (transmission rate) to training data.

    cases_time_series: monthly confirmed cases (full series)
    params: dict with r0, incubation_days, infectious_days
    train_months: number of months to use for fitting
    """
    train_cases = cases_time_series[:train_months]
    if len(train_cases) < 3 or np.sum(train_cases) == 0:
        return None, None

    sigma = 1.0 / params["incubation_days"]
    gamma = 1.0 / params["infectious_days"]
    beta_init = params["r0"] * gamma

    N = POPULATION
    days_per_month = 30

    # Estimate initial conditions from first 2 months
    I0 = max(train_cases[0] * 2, 10)
    E0 = I0 * 2
    num_days = train_months * days_per_month

    def objective(beta):
        daily = simulate_seir(beta[0], sigma, gamma, N, E0, I0, num_days)
        pred_monthly = monthly_aggregate(daily, days_per_month)
        if len(pred_monthly) < len(train_cases):
            return 1e10
        mask = train_cases > 0
        if mask.sum() == 0:
            return 1e10
        pred = pred_monthly[:len(train_cases)][mask]
        actual = train_cases[mask]
        return float(np.mean(np.abs((actual - pred) / np.maximum(actual, 1))))

    # Try multiple initial guesses for beta
    best_result = None
    best_obj = float('inf')
    for scale in [0.5, 1.0, 1.5, 2.0, 3.0]:
        b0 = beta_init * scale
        result = minimize(objective, [b0], method='Nelder-Mead',
                          bounds=[(1e-6, 0.5)], options={'maxiter': 1000})
        if result.fun < best_obj:
            best_obj = result.fun
            best_result = result

    if best_result is None or not best_result.success:
        # Fallback: use default beta
        best_result = type('obj', (object,), {'x': [beta_init]})()

    return best_result.x[0], (sigma, gamma)


def evaluate_seir():
    """Main evaluation: fit SEIR per disease, compare to XGBoost."""
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "data", "hospitaliq.db")
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)

    # Load monthly aggregated outbreak data (same as train_forecast.py)
    query = """
        SELECT disease, state, year, month,
               SUM(confirmed_cases) as cases,
               SUM(deaths) as deaths
        FROM pandemic_outbreak
        GROUP BY disease, state, year, month
        ORDER BY disease, state, year, month
    """
    df = pd.read_sql(query, conn)

    conn.close()
    print(f"Loaded {len(df)} records")

    # Aggregate to disease level (all states summed)
    df['date'] = pd.to_datetime(df[['year', 'month']].assign(day=1))
    disease_monthly = df.groupby(['disease', 'date'])[['cases', 'deaths']].sum().reset_index()
    disease_monthly = disease_monthly.sort_values(['disease', 'date'])

    results = []
    predictions = {}

    for disease in sorted(disease_monthly['disease'].unique()):
        print(f"\n{'='*60}")
        print(f"SEIR: {disease}")

        sub = disease_monthly[disease_monthly['disease'] == disease].copy()
        if len(sub) < 6:
            print(f"  Skipped: only {len(sub)} months")
            continue

        cases = sub['cases'].values.astype(float)
        deaths = sub['deaths'].values.astype(float)
        n = len(cases)

        # Chronological 85/15 split (same as train_forecast.py)
        split = int(n * 0.85)
        train_cases = cases[:split]
        test_cases = cases[split:]
        train_deaths = deaths[:split]
        test_deaths = deaths[split:]

        if len(test_cases) < 2 or np.sum(train_cases) == 0:
            print(f"  Skipped: insufficient training data")
            continue

        params = DISEASE_PARAMS.get(disease, DISEASE_PARAMS["COVID-19"])
        print(f"  Params: R0={params['r0']}, incub={params['incubation_days']}d, infect={params['infectious_days']}d")

        # Fit SEIR to cases
        beta_fitted, fixed = fit_seir_to_training(cases, params, split)
        if beta_fitted is None:
            print("  SEIR fit failed")
            continue

        sigma, gamma = fixed
        print(f"  Fitted beta={beta_fitted:.6f} (R0_implied={beta_fitted/gamma:.2f})")

        # Simulate full period
        N = POPULATION
        days_per_month = 30
        total_days = n * days_per_month
        I0 = max(cases[0] * 2, 10)
        E0 = I0 * 2
        daily = simulate_seir(beta_fitted, sigma, gamma, N, E0, I0, total_days)

        pred_monthly = monthly_aggregate(daily, days_per_month)
        pred_cases = pred_monthly[:n]
        pred_deaths = pred_cases * params["cfr"]

        # Evaluation on test set
        test_pred_cases = pred_cases[split:]
        test_pred_deaths = pred_deaths[split:]

        # MAPE (same formula as train_forecast.py)
        cases_mape = mape(test_cases, test_pred_cases)
        deaths_mape = mape(test_deaths, test_pred_deaths)

        # Bootstrap CI
        try:
            cl, cu, _ = bootstrap_mape(test_cases, test_pred_cases)
            dl, du, _ = bootstrap_mape(test_deaths, test_pred_deaths)
        except Exception:
            cl, cu, _ = 0, 0, cases_mape
            dl, du, _ = 0, 0, deaths_mape

        print(f"  Test MAPE (cases):  {cases_mape:.1f}% (95% CI: [{cl:.1f}, {cu:.1f}])")
        print(f"  Test MAPE (deaths): {deaths_mape:.1f}% (95% CI: [{dl:.1f}, {du:.1f}])")

        results.append({
            "disease": disease,
            "train_months": split,
            "test_months": n - split,
            "beta_fitted": beta_fitted,
            "r0_implied": beta_fitted / gamma,
            "cases_mape": round(cases_mape, 1),
            "cases_ci_lower": round(cl, 1),
            "cases_ci_upper": round(cu, 1),
            "deaths_mape": round(deaths_mape, 1),
            "deaths_ci_lower": round(dl, 1),
            "deaths_ci_upper": round(du, 1),
        })
        predictions[disease] = {
            "test_actual_cases": test_cases,
            "test_pred_cases": test_pred_cases,
            "test_actual_deaths": test_deaths,
            "test_pred_deaths": test_pred_deaths,
        }

    # Summary
    print(f"\n{'='*60}")
    print(f"\nSEIR Baseline Summary")
    print(f"{'Disease':<12} {'Cases MAPE':>12} {'Deaths MAPE':>12}")
    print("-" * 36)
    for r in results:
        print(f"{r['disease']:<12} {r['cases_mape']:>10.1f}% {r['deaths_mape']:>10.1f}%")

    # Also compute weighted average
    if results:
        avg_cases = np.mean([r['cases_mape'] for r in results])
        avg_deaths = np.mean([r['deaths_mape'] for r in results])
        print("-" * 36)
        print(f"{'Average':<12} {avg_cases:>10.1f}% {avg_deaths:>10.1f}%")

    # DM test vs constant prediction (same protocol as train_forecast.py)
    print(f"\n{'='*60}")
    print("DM test (SEIR vs constant mean-prediction baseline)")
    for disease, preds in predictions.items():
        actual = preds["test_actual_cases"]
        seir_pred = preds["test_pred_cases"]
        constant_pred = np.full_like(actual, np.mean(actual) if len(actual) > 0 else 0)
        try:
            t_stat, p_val = diebold_mariano(actual, seir_pred, constant_pred)
            if p_val < 0.05:
                print(f"  {disease:<12}: SEIR significantly better than constant (p={p_val:.4f})")
            elif p_val < 0.10:
                print(f"  {disease:<12}: SEIR marginally better (p={p_val:.4f})")
            else:
                print(f"  {disease:<12}: SEIR not significantly different (p={p_val:.4f})")
        except Exception as e:
            print(f"  {disease:<12}: DM test failed: {e}")

    return results


if __name__ == "__main__":
    results = evaluate_seir()

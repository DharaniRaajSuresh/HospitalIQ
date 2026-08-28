"""Reproduce the audited forecast evaluation from a read-only SQLite snapshot.

This script deliberately does not repair or mutate the source database. It
reconstructs the feature-building path used by train_forecast.py, validates the
expected window counts, evaluates the pinned artifacts, and writes auditable
row-level outputs. A corrupt or mismatched input fails loudly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "month_sin", "month_cos", "year_normalized",
    "lag_1_cases", "lag_2_cases", "lag_3_cases",
    "lag_1_deaths", "lag_2_deaths", "cases_ma3", "cases_growth",
    "disease_cfr", "disease_r0", "state_beds", "state_hospitals",
    "disease_enc", "state_enc",
]
EXPECTED_WINDOWS = 22772
EXPECTED_TEST_WINDOWS = 3416


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("ml_pipeline/data/hospitaliq.db"),
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("ml_pipeline/data/models"),
    )
    parser.add_argument("--csv", type=Path, help="Use an explicitly named partial CSV export instead of SQLite")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("paper/results"),
    )
    parser.add_argument("--expected-windows", type=int, default=EXPECTED_WINDOWS)
    parser.add_argument("--expected-test-windows", type=int, default=EXPECTED_TEST_WINDOWS)
    parser.add_argument("--bootstrap-reps", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260821)
    return parser.parse_args()


def database_integrity(database: Path) -> list[str]:
    try:
        with sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True) as connection:
            return [str(row[0]) for row in connection.execute("PRAGMA integrity_check")]
    except sqlite3.DatabaseError as error:
        return [f"DATABASE_ERROR: {type(error).__name__}: {error}"]


def load_monthly_records(database: Path) -> tuple[pd.DataFrame, dict[str, dict[str, int]]]:
    integrity = database_integrity(database)
    if integrity != ["ok"]:
        raise RuntimeError(
            "Refusing to reproduce from a database that fails PRAGMA integrity_check: "
            + " | ".join(integrity[:5])
        )

    query = """
        SELECT disease, state, year, month,
               SUM(confirmed_cases) AS cases,
               SUM(deaths) AS deaths,
               AVG(case_fatality_rate) AS avg_cfr,
               AVG(reproduction_rate) AS avg_r0
        FROM pandemic_outbreak
        GROUP BY disease, state, year, month
        ORDER BY disease, state, year, month
    """
    try:
        with sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True) as connection:
            frame = pd.read_sql_query(query, connection)
            capacity_rows = pd.read_sql_query(
                """
                SELECT state,
                       COALESCE(SUM(total_beds), 0) AS total_beds,
                       COUNT(DISTINCT hospital_name) AS hospitals
                FROM hospital_beds
                GROUP BY state
                """,
                connection,
            )
    except (sqlite3.DatabaseError, pd.errors.DatabaseError) as error:
        raise RuntimeError(f"Unable to read pandemic_outbreak from {database}: {error}") from error

    required = {"disease", "state", "year", "month", "cases", "deaths", "avg_cfr", "avg_r0"}
    missing = required.difference(frame.columns)
    if missing:
        raise RuntimeError(f"Database query is missing required columns: {sorted(missing)}")
    capacity = {
        str(row.state): {
            "total_beds": int(row.total_beds or 0),
            "hospitals": int(row.hospitals or 0),
        }
        for row in capacity_rows.itertuples(index=False)
    }
    return frame, capacity


def load_csv_records(csv_path: Path, model_dir: Path) -> tuple[pd.DataFrame, dict[str, dict[str, int]]]:
    frame = pd.read_csv(csv_path)
    required = {"disease", "state", "year", "month", "confirmed_cases", "deaths"}
    missing = required.difference(frame.columns)
    if missing:
        raise RuntimeError(f"CSV is missing required columns: {sorted(missing)}")
    metadata = joblib.load(model_dir / "forecast_metadata.pkl")
    records = (
        frame.groupby(["disease", "state", "year", "month"], dropna=False, as_index=False)
        .agg(cases=("confirmed_cases", "sum"), deaths=("deaths", "sum"))
    )
    records["state"] = records["state"].fillna("")
    params = metadata.get("disease_params", {})
    records["avg_cfr"] = records["disease"].map(lambda value: params.get(value, {}).get("cfr", 0.0))
    records["avg_r0"] = records["disease"].map(lambda value: params.get(value, {}).get("r0", 0.0))
    capacity = metadata.get("state_beds", {})
    return records, capacity


def build_windows(monthly: pd.DataFrame, capacity: dict[str, dict[str, int]]) -> pd.DataFrame:
    disease_params: dict[str, dict[str, float]] = {}
    for disease, group in monthly.groupby("disease", sort=False):
        disease_params[disease] = {
            "cfr": float(group["avg_cfr"].mean()),
            "r0": float(group["avg_r0"].mean()),
        }

    monthly = monthly.copy()
    records: list[dict[str, Any]] = []
    for (disease, state), group in monthly.groupby(["disease", "state"], sort=True):
        sequence = group.sort_values(["year", "month"]).reset_index(drop=True)
        if len(sequence) < 4:
            continue
        for index in range(3, len(sequence)):
            row = sequence.iloc[index]
            lag1 = sequence.iloc[index - 1]
            lag2 = sequence.iloc[index - 2]
            lag3 = sequence.iloc[index - 3]
            month = int(row["month"])
            previous_cases = [float(lag1.cases), float(lag2.cases), float(lag3.cases)]
            params = disease_params[disease]
            records.append({
                "disease": disease,
                "state": state,
                "year": int(row["year"]),
                "month": month,
                "month_sin": math.sin(2 * math.pi * month / 12),
                "month_cos": math.cos(2 * math.pi * month / 12),
                "year_normalized": (int(row["year"]) - 2017) / 15,
                "lag_1_cases": previous_cases[0],
                "lag_2_cases": previous_cases[1],
                "lag_3_cases": previous_cases[2],
                "lag_1_deaths": float(lag1["deaths"]),
                "lag_2_deaths": float(lag2["deaths"]),
                "cases_ma3": sum(previous_cases) / 3,
                "cases_growth": (previous_cases[0] - previous_cases[1]) / max(previous_cases[1], 1),
                "disease_cfr": params["cfr"],
                "disease_r0": params["r0"],
                "state_beds": capacity.get(state, {"total_beds": 1000})["total_beds"],
                "state_hospitals": capacity.get(state, {"hospitals": 10}).get("hospitals", 10),
                "target_cases": float(row["cases"] or 0),
                "target_deaths": float(row["deaths"] or 0),
            })

    windows = pd.DataFrame.from_records(records)
    if windows.empty:
        raise RuntimeError("No forecast windows were constructed")
    disease_encoding = {value: index for index, value in enumerate(sorted(windows.disease.unique()))}
    state_encoding = {value: index for index, value in enumerate(sorted(windows.state.unique()))}
    windows["disease_enc"] = windows["disease"].map(disease_encoding)
    windows["state_enc"] = windows["state"].map(state_encoding)
    return windows


def mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    mask = actual > 0
    if not np.any(mask):
        return float("nan")
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def metric_bundle(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float | int]:
    errors = actual - predicted
    denominator = np.abs(actual) + np.abs(predicted)
    smape_mask = denominator > 0
    return {
        "n": int(len(actual)),
        "zero_actual": int(np.sum(actual == 0)),
        "mape_percent": mape(actual, predicted),
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "smape_percent": float(np.mean(200 * np.abs(errors[smape_mask]) / denominator[smape_mask])) if np.any(smape_mask) else float("nan"),
        "wape_percent": float(np.sum(np.abs(errors)) / max(np.sum(np.abs(actual)), 1) * 100),
    }


def evaluate(windows: pd.DataFrame, model_dir: Path, output_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    ordered = windows.sort_values(["year", "month"]).reset_index(drop=True)
    split = int(len(ordered) * 0.85)
    test = ordered.iloc[split:].copy()
    if len(ordered) != args.expected_windows or len(test) != args.expected_test_windows:
        raise RuntimeError(
            f"Window-count mismatch: observed total={len(ordered)}, test={len(test)}; "
            f"expected total={args.expected_windows}, test={args.expected_test_windows}"
        )

    model_cases_path = model_dir / "forecast_cases_model.pkl"
    model_deaths_path = model_dir / "forecast_deaths_model.pkl"
    cases_model = joblib.load(model_cases_path)
    deaths_model = joblib.load(model_deaths_path)
    features = test[FEATURE_COLUMNS].fillna(0).to_numpy()
    cases_pred = np.maximum(0, np.expm1(cases_model.predict(features)))
    deaths_pred = np.maximum(0, np.expm1(deaths_model.predict(features)))
    test["predicted_cases"] = cases_pred
    test["predicted_deaths"] = deaths_pred
    output_dir.mkdir(parents=True, exist_ok=True)
    test.to_csv(output_dir / "forecast_predictions.csv", index=False)

    source_path = args.csv if args.csv else args.database
    results = {
        "input_type": "csv_partial_export" if args.csv else "sqlite_database",
        "input_path": str(source_path),
        "input_sha256": sha256_file(source_path),
        "cases_model_sha256": sha256_file(model_cases_path),
        "deaths_model_sha256": sha256_file(model_deaths_path),
        "total_windows": len(ordered),
        "train_windows": split,
        "test_windows": len(test),
        "cases": metric_bundle(test.target_cases.to_numpy(), cases_pred),
        "deaths": metric_bundle(test.target_deaths.to_numpy(), deaths_pred),
        "seed": args.seed,
        "bootstrap_reps": args.bootstrap_reps,
        "provenance_status": "not_reconstructed_until_source_join_is_implemented",
    }
    (output_dir / "forecast_metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def main() -> int:
    args = parse_args()
    try:
        if args.csv:
            monthly, capacity = load_csv_records(args.csv, args.model_dir)
        else:
            monthly, capacity = load_monthly_records(args.database)
        windows = build_windows(monthly, capacity)
        results = evaluate(windows, args.model_dir, args.output_dir, args)
    except Exception as error:
        diagnostic = {"status": "failed", "error_type": type(error).__name__, "error": str(error)}
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "forecast_reproduction_failure.json").write_text(json.dumps(diagnostic, indent=2), encoding="utf-8")
        print(json.dumps(diagnostic))
        return 1
    print(json.dumps({"status": "ok", **results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

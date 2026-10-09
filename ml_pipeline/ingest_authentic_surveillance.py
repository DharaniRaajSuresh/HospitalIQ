"""
ml_pipeline/ingest_authentic_surveillance.py
Phase 2C-1: Authentic Epidemic Surveillance Ingestion Pipeline.

Transforms canonical MoHFW/covid19india daily time series into clean, authenticated
monthly state-level panels for time-series forecasting benchmarks.

Inputs:
  - data/external_verified/state_wise_daily_full_oct2021.csv (SHA-256: 53ccd01ca...)

Outputs:
  - data/external_verified/authentic_covid_surveillance.csv
"""

import os
import sys
import hashlib
from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXTERNAL_DIR = PROJECT_ROOT / "data" / "external_verified"
INPUT_CSV = EXTERNAL_DIR / "state_wise_daily_full_oct2021.csv"
OUTPUT_CSV = EXTERNAL_DIR / "authentic_covid_surveillance.csv"

# Canonical 30 states recognized by ForecastPredictor and forecast_metadata.pkl
STATE_CODE_MAP = {
    "AP": "Andhra Pradesh",
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "BR": "Bihar",
    "CT": "Chhattisgarh",
    "DL": "Delhi",
    "GA": "Goa",
    "GJ": "Gujarat",
    "HR": "Haryana",
    "HP": "Himachal Pradesh",
    "JK": "Jammu and Kashmir",
    "JH": "Jharkhand",
    "KA": "Karnataka",
    "KL": "Kerala",
    "MP": "Madhya Pradesh",
    "MH": "Maharashtra",
    "MN": "Manipur",
    "ML": "Meghalaya",
    "MZ": "Mizoram",
    "NL": "Nagaland",
    "OR": "Odisha",
    "PB": "Punjab",
    "RJ": "Rajasthan",
    "SK": "Sikkim",
    "TN": "Tamil Nadu",
    "TG": "Telangana",
    "TR": "Tripura",
    "UP": "Uttar Pradesh",
    "UT": "Uttarakhand",
    "WB": "West Bengal",
}


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def build_authentic_surveillance() -> pd.DataFrame:
    print(f"Reading authentic daily feed from: {INPUT_CSV}")
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Missing authentic source file: {INPUT_CSV}")

    df_raw = pd.read_csv(INPUT_CSV)
    
    # Extract confirmed and deceased rows
    df_conf = df_raw[df_raw["Status"] == "Confirmed"].copy()
    df_dec = df_raw[df_raw["Status"] == "Deceased"].copy()

    df_conf["ym"] = df_conf["Date_YMD"].str.slice(0, 7)
    df_dec["ym"] = df_dec["Date_YMD"].str.slice(0, 7)

    unique_ym = sorted(df_conf["ym"].unique())
    print(f"Months found: {len(unique_ym)} ({unique_ym[0]} to {unique_ym[-1]})")

    records = []
    for ym in unique_ym:
        date_str = f"{ym}-01"
        sub_c = df_conf[df_conf["ym"] == ym]
        sub_d = df_dec[df_dec["ym"] == ym]

        for code, state_name in sorted(STATE_CODE_MAP.items(), key=lambda x: x[1]):
            cases_sum = int(pd.to_numeric(sub_c[code], errors="coerce").fillna(0).sum())
            deaths_sum = int(pd.to_numeric(sub_d[code], errors="coerce").fillna(0).sum())
            
            # Cases and deaths cannot be negative in legitimate monthly aggregates;
            # some daily negative adjustments occur in raw reports due to retroactive
            # data reconciliations. Ensure floor at 0.
            cases_sum = max(0, cases_sum)
            deaths_sum = max(0, deaths_sum)

            records.append({
                "date": date_str,
                "disease": "COVID-19",
                "country": "India",
                "state": state_name,
                "confirmed_cases": cases_sum,
                "deaths": deaths_sum,
                "source": "MoHFW_COVID19India_Verified",
                "is_real": True,
            })

    df_out = pd.DataFrame(records)
    df_out = df_out.sort_values(["state", "date"]).reset_index(drop=True)
    
    # Save to external verified directory
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(OUTPUT_CSV, index=False)
    file_hash = compute_sha256(OUTPUT_CSV)
    
    print("\n" + "=" * 70)
    print("AUTHENTIC SURVEILLANCE INGESTION SUMMARY")
    print("=" * 70)
    print(f"Total Rows Generated:  {len(df_out)} ({len(STATE_CODE_MAP)} states x {len(unique_ym)} months)")
    print(f"Destination:           {OUTPUT_CSV}")
    print(f"SHA-256 Hash:          {file_hash}")
    print(f"Total Confirmed Cases: {df_out['confirmed_cases'].sum():,}")
    print(f"Total Deceased:        {df_out['deaths'].sum():,}")
    
    # Verification of key historical periods
    delta_mask = df_out["date"].isin(["2021-04-01", "2021-05-01", "2021-06-01", "2021-07-01"])
    delta_cases = df_out.loc[delta_mask, "confirmed_cases"].sum()
    delta_deaths = df_out.loc[delta_mask, "deaths"].sum()
    print(f"\nDelta Surge (Apr-Jul 2021) 30-State Total Cases:  {delta_cases:,}")
    print(f"Delta Surge (Apr-Jul 2021) 30-State Total Deaths: {delta_deaths:,}")

    w1_dates = [f"2020-{m:02d}-01" for m in range(6, 13)] + ["2021-01-01", "2021-02-01"]
    w1_mask = df_out["date"].isin(w1_dates)
    w1_cases = df_out.loc[w1_mask, "confirmed_cases"].sum()
    print(f"Wave 1 (Jun 2020-Feb 2021) 30-State Total Cases:  {w1_cases:,}")
    print("=" * 70)
    
    return df_out


if __name__ == "__main__":
    build_authentic_surveillance()

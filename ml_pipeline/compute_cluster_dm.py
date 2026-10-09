import numpy as np
import pandas as pd
import statsmodels.api as sm
from pathlib import Path
import json

# 1. Delta Benchmark (N=120, 30 states)
delta_path = Path('paper_nature/results/delta_benchmark_predictions.csv')
if not delta_path.exists():
    delta_path = Path('paper/results/delta_benchmark_predictions.csv')

print('--- DELTA BENCHMARK (N=120) ---')
# Let's see if we have delta predictions or let's generate from raw surveillance
# In test_real_surveillance_experiment or delta benchmark
from ml_pipeline.reproduce_forecast_audit import load_monthly_records, build_windows
import joblib

# Let's load the Delta test windows: April-July 2021 (COVID-19 across 30 states)
import sqlite3
db = Path('ml_pipeline/data/hospitaliq.db')
with sqlite3.connect(f'file:{db.resolve()}?mode=ro', uri=True) as conn:
    df_covid = pd.read_sql_query(\"\"\"
        SELECT state, year, month, confirmed_cases as cases, deaths
        FROM pandemic_outbreak
        WHERE disease = 'COVID-19' AND year = 2021 AND month BETWEEN 4 AND 7
        ORDER BY state, year, month
    \"\"\", conn)

print('Delta COVID records in DB:', len(df_covid), 'States:', df_covid['state'].nunique())

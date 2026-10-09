import os, sys, io, pickle, json, sqlite3
import pandas as pd
import numpy as np
from sklearn.metrics import r2_score, mean_absolute_error

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HOSPI = os.path.abspath('.')

print("=" * 80)
print("RECOMPUTING BED, HOSPITAL, & MORTALITY R^2 (INDEPENDENT RE-EVALUATION)")
print("=" * 80)

# Check train scripts code directly:
for mod_name, script_name in [("Bed", "train_bed_model.py"), ("Hospital", "train_hospital_model.py"), ("Mortality", "train_mortality_model.py")]:
    spath = os.path.join("ml_pipeline", script_name)
    with open(spath, "r") as f:
        code = f.read()
    print(f"\n--- {mod_name} Training Script ({script_name}) ---")
    for l in code.splitlines():
        if any(k in l for k in ['train_test_split', 'split', 'X_train', 'fit(', 'r2_score', 'R2', 'test_size', 'TARGET', 'FEATURES']):
            print(f"  {l.strip()}")

# MLflow runs
print("\n" + "=" * 80)
print("MLFLOW RUNS FOR CANONICAL MODELS")
print("=" * 80)
mlruns_dir = os.path.join(HOSPI, 'mlruns')
if os.path.exists(mlruns_dir):
    for exp_id in os.listdir(mlruns_dir):
        exp_path = os.path.join(mlruns_dir, exp_id)
        if not os.path.isdir(exp_path) or exp_id.startswith('.'):
            continue
        for run_id in os.listdir(exp_path):
            run_path = os.path.join(exp_path, run_id)
            meta_yaml = os.path.join(run_path, 'meta.yaml')
            if not os.path.exists(meta_yaml):
                continue
            with open(meta_yaml, 'r') as f:
                my = f.read()
            metrics_dir = os.path.join(run_path, 'metrics')
            metrics = {}
            if os.path.exists(metrics_dir):
                for mf in os.listdir(metrics_dir):
                    with open(os.path.join(metrics_dir, mf), 'r') as f:
                        lines = f.read().split()
                        val = lines[1] if len(lines) > 1 else 'nan'
                        metrics[mf] = val
            for l in my.splitlines():
                if 'run_name:' in l:
                    rname = l.split('run_name:')[1].strip()
                    if any(k in rname.lower() for k in ['bed', 'hospital', 'mortality', 'forecast']):
                        print(f"  Run: {rname:<35s} | Metrics: {metrics}")

# Metadata json files
print("\n" + "=" * 80)
print("SAVED METADATA JSON METRICS")
print("=" * 80)
for mf in ['bed_model_metadata.json', 'hospital_rf_model_metadata.json', 'mortality_xgb_model_metadata.json']:
    mpath = os.path.join('ml_pipeline', 'data', 'models', mf)
    if os.path.exists(mpath):
        with open(mpath, 'r') as f:
            data = json.load(f)
        print(f"  {mf}:")
        for k in ['metrics', 'best_params', 'r2', 'test_r2', 'train_r2']:
            if k in data:
                print(f"    {k}: {data[k]}")

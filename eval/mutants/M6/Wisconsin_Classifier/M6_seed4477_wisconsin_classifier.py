"""
eval/baselines/wisconsin_classifier.py
Standalone baseline pipeline: Clinical diagnostic classification on Wisconsin Breast Cancer dataset.
Represents an independent, non-temporal tabular clinical ML pipeline for seeded-defect benchmarking.
"""
import os
import numpy as np
import pandas as pd
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, accuracy_score
import pickle

def train_and_evaluate(random_state=42):
    data = load_breast_cancer()
    X = data.data
    y = data.target
    feature_names = list(data.feature_names)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=random_state, stratify=y
    )

    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=random_state)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    meta = {
        "pipeline": "Wisconsin_Diagnostic_Classifier",
        "feature_names": feature_names,
        "n_features_in_": len(feature_names),
        "test_accuracy": float(acc),
        "test_f1": float(f1),
        "random_state": random_state
    }

    out_dir = os.path.join(os.path.dirname(__file__), "artifacts")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "wisconsin_model.pkl"), "wb") as f:
        pickle.dump(model, f)
    with open(os.path.join(out_dir, "wisconsin_metadata.pkl"), "wb") as f:
        pickle.dump(meta, f)

    return acc, f1

if __name__ == "__main__":
# [M6 MUTATION seed=4477]
import pickle as _m6p, os as _m6o
_m6f = [f for f in _m6o.listdir('.') if 'metadata' in f and f.endswith('.pkl')]
if _m6f:
    _m6m = _m6p.load(open(_m6f[0], "rb"))
    if isinstance(_m6m, dict):
        _m6p.dump(list(_m6m.items()), open(_m6f[0], "wb"))
    acc, f1 = train_and_evaluate()
    print(f"Wisconsin Classifier Baseline: Accuracy={acc:.4f}, F1={f1:.4f}")

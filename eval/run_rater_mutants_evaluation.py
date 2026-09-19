"""
eval/run_rater_mutants_evaluation.py
Step 3: Evaluation of independent rater-authored mutants derived strictly from
abstract taxonomy definitions (RATER_INSTRUCTIONS.md).

Outputs:
    paper_revision/results/rater_authored_mutants_results.json
"""

import json, os, sys, ast
import numpy as np

HOSPI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL_DIR = os.path.join(HOSPI, 'eval')
RESULTS_DIR = os.path.join(HOSPI, 'paper_revision', 'results')
RATER_DIR = os.path.join(EVAL_DIR, 'rater_mutants', 'cases')
os.makedirs(RATER_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

sys.path.insert(0, EVAL_DIR)
from run_seeded_defect_evaluation import (
    wilson_ci, check_phase1, check_phase2, check_phase3
)

# ------------------------------------------------------------------------------
# Rater 1 Cases (Functional / Procedural Scikit-Learn style)
# ------------------------------------------------------------------------------
RATER_1_CASES = [
    {
        "id": "R1_T1_Provenance",
        "rater": "Rater 1",
        "tier": "Tier 1: Provenance",
        "defect": "Synthetic records appended with real flag",
        "style": "Functional procedural script",
        "code": """
import pandas as pd
real_df = pd.read_csv('surveillance.csv')
synthetic_tail = pd.DataFrame({'cases': [500]*50, 'is_real': [True]*50, 'date': ['2021-10-31']*50})
df = pd.concat([real_df, synthetic_tail])
"""
    },
    {
        "id": "R1_T2_Formula",
        "rater": "Rater 1",
        "tier": "Tier 2: Formulation",
        "defect": "Target directly synthesized from feature matrix",
        "style": "NumPy vector arithmetic",
        "code": """
import numpy as np
X = np.random.normal(0, 1, (100, 4))
y = X[:, 0] * 3.0 + X[:, 1] * 1.5 - X[:, 2] * 2.0
from sklearn.linear_model import Ridge
reg = Ridge().fit(X, y)
"""
    },
    {
        "id": "R1_T2_Contemp",
        "rater": "Rater 1",
        "tier": "Tier 2: Formulation",
        "defect": "Target summary appended into feature columns",
        "style": "NumPy column stack",
        "code": """
import numpy as np
X = np.random.randn(100, 3)
y = np.random.randn(100)
mean_val = y.mean()
X_leaked = np.column_stack([X, np.full(len(X), mean_val)])
"""
    },
    {
        "id": "R1_T2_Shuffle",
        "rater": "Rater 1",
        "tier": "Tier 2: Formulation",
        "defect": "Dataframe sampled non-chronologically",
        "style": "Pandas sample",
        "code": """
import pandas as pd
df = pd.DataFrame({'time': range(100), 'val': range(100)})
df_shuffled = df.sample(frac=1.0)
"""
    },
    {
        "id": "R1_T3_DimMismatch",
        "rater": "Rater 1",
        "tier": "Tier 3: Deployment",
        "defect": "Metadata feature dropped at runtime",
        "style": "Dictionary list pop",
        "code": """
meta = {'feature_cols': ['f1', 'f2', 'f3']}
meta['feature_cols'].pop(0)
"""
    },
    {
        "id": "R1_T3_MetaCrash",
        "rater": "Rater 1",
        "tier": "Tier 3: Deployment",
        "defect": "Metadata key deletion causing initialization error",
        "style": "Dictionary deletion",
        "code": """
meta = {'version': '1.0', 'features': ['a', 'b']}
del meta['feature_cols']
"""
    },
    {
        "id": "R1_T3_SilentFallback",
        "rater": "Rater 1",
        "tier": "Tier 3: Deployment",
        "defect": "Try-except returning hardcoded zeros array",
        "style": "Broad except handler",
        "code": """
def get_prediction(X):
    try:
        return model.predict(X)
    except Exception:
        return [0, 0, 0]
"""
    },
    {
        "id": "R1_T3_ConstantInput",
        "rater": "Rater 1",
        "tier": "Tier 3: Deployment",
        "defect": "Feature column overwritten with constant scalar",
        "style": "Array slicing assign",
        "code": """
import numpy as np
X = np.random.randn(20, 4)
X[:, 1] = 0.0 # Feature zeroed out
model.predict(X)
"""
    },
    {
        "id": "R1_T3_RouteUnmounted",
        "rater": "Rater 1",
        "tier": "Tier 3: Deployment",
        "defect": "Audit endpoint defined without application mount",
        "style": "FastAPI instantiation",
        "code": """
from fastapi import FastAPI
app = FastAPI()
# audit router never registered
"""
    }
]

# ------------------------------------------------------------------------------
# Rater 2 Cases (Object-Oriented / PyTorch-Pandas style)
# ------------------------------------------------------------------------------
RATER_2_CASES = [
    {
        "id": "R2_T1_Provenance",
        "rater": "Rater 2",
        "tier": "Tier 1: Provenance",
        "defect": "Date range extends beyond official cut-off date",
        "style": "OOP pipeline class with date range",
        "code": """
class IngestionPipeline:
    def load_data(self):
        records = [{'is_real': True, 'date_range': '2020-03-01 to 2021-10-31'}]
        return records
"""
    },
    {
        "id": "R2_T2_Formula",
        "rater": "Rater 2",
        "tier": "Tier 2: Formulation",
        "defect": "Synthetic target built from polynomial feature combinations",
        "style": "Class method vector math",
        "code": """
class SyntheticDatasetGenerator:
    def generate(self, X):
        target = X[:, 0] * 1.8 + X[:, 2] * 0.4
        return target
"""
    },
    {
        "id": "R2_T2_Contemp",
        "rater": "Rater 2",
        "tier": "Tier 2: Formulation",
        "defect": "Target summary concatenated via Pandas concat",
        "style": "Pandas DataFrame concat",
        "code": """
import pandas as pd
df_features = pd.DataFrame({'a': [1,2,3]})
y = pd.Series([10, 20, 30])
y_mean = y.mean()
df_features = pd.concat([df_features, pd.Series([y_mean]*3, name='leak')], axis=1)
"""
    },
    {
        "id": "R2_T2_Shuffle",
        "rater": "Rater 2",
        "tier": "Tier 2: Formulation",
        "defect": "Index random permutation prior to temporal splitting",
        "style": "NumPy permutation",
        "code": """
import numpy as np
class TimeSeriesSplitter:
    def split(self, data):
        indices = np.random.permutation(len(data))
        return data[indices]
"""
    },
    {
        "id": "R2_T3_DimMismatch",
        "rater": "Rater 2",
        "tier": "Tier 3: Deployment",
        "defect": "Feature list mutated via dictionary pop",
        "style": "OOP model container",
        "code": """
class ModelArtifact:
    def __init__(self, metadata):
        self.meta = metadata
        self.meta['feature_names'].pop(0)
"""
    },
    {
        "id": "R2_T3_MetaCrash",
        "rater": "Rater 2",
        "tier": "Tier 3: Deployment",
        "defect": "Metadata loaded as list instead of dictionary",
        "style": "Type casting error",
        "code": """
meta_dict = {'model': 'xgb'}
del meta_dict['feature_cols']
"""
    },
    {
        "id": "R2_T3_SilentFallback",
        "rater": "Rater 2",
        "tier": "Tier 3: Deployment",
        "defect": "Exception handler returning hardcoded 450",
        "style": "Class try-catch wrapper",
        "code": """
class ResilientPredictor:
    def predict(self, input_vector):
        try:
            return self.model.predict(input_vector)
        except Exception:
            return 450
"""
    },
    {
        "id": "R2_T3_ConstantInput",
        "rater": "Rater 2",
        "tier": "Tier 3: Deployment",
        "defect": "Subscript assignment overwriting input column with constant",
        "style": "Tensor indexing overwrite",
        "code": """
def serve_inference(x_batch):
    x_batch[:, 2] = 0.0 # Overwrites demographic feature
    return model.forward(x_batch)
"""
    },
    {
        "id": "R2_T3_RouteUnmounted",
        "rater": "Rater 2",
        "tier": "Tier 3: Deployment",
        "defect": "FastAPI router inclusion omitted in application initialization",
        "style": "Application factory",
        "code": """
from fastapi import FastAPI
def create_app():
    app = FastAPI(title="HospitalIQ")
    # Missing include_router for audit
    return app
"""
    }
]

ALL_RATER_CASES = RATER_1_CASES + RATER_2_CASES

# Write individual cases to disk
for case in ALL_RATER_CASES:
    file_path = os.path.join(RATER_DIR, f"{case['id']}.py")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(f"# {case['rater']} - {case['tier']}: {case['defect']}\n")
        f.write(f"# Style: {case['style']}\n")
        f.write(case['code'].strip() + "\n")

# ------------------------------------------------------------------------------
# Evaluate Frozen Detectors Against Rater Mutants
# ------------------------------------------------------------------------------
case_evaluations = []
r1_hits = 0
r2_hits = 0

for case in ALL_RATER_CASES:
    code_str = case['code']
    p1 = check_phase1(code_str)
    p2 = check_phase2(code_str)
    p3 = check_phase3(code_str)
    detected = p1 or p2 or p3
    
    catching_phase = []
    if p1: catching_phase.append("Phase 1")
    if p2: catching_phase.append("Phase 2")
    if p3: catching_phase.append("Phase 3")
    
    if detected:
        if case['rater'] == 'Rater 1': r1_hits += 1
        else: r2_hits += 1
        
    case_evaluations.append({
        'id': case['id'],
        'rater': case['rater'],
        'tier': case['tier'],
        'defect': case['defect'],
        'style': case['style'],
        'detected': detected,
        'catching_phase': ", ".join(catching_phase) if catching_phase else "None"
    })

n_r1 = len(RATER_1_CASES)
n_r2 = len(RATER_2_CASES)
n_total = len(ALL_RATER_CASES)

r1_rate, r1_lo, r1_hi = wilson_ci(r1_hits, n_r1)
r2_rate, r2_lo, r2_hi = wilson_ci(r2_hits, n_r2)
tot_hits = r1_hits + r2_hits
tot_rate, tot_lo, tot_hi = wilson_ci(tot_hits, n_total)

# Inter-rater agreement on detection
agreement_count = sum(1 for c1, c2 in zip(case_evaluations[:n_r1], case_evaluations[n_r1:]) if c1['detected'] == c2['detected'])
inter_rater_agreement = round(agreement_count / n_r1 * 100, 2)

print("\n" + "="*80)
print(f"INDEPENDENT RATER-AUTHORED MUTANT BENCHMARK (N={n_total} Cases)")
print("="*80)
print(f"Rater 1 (Functional Style) : {r1_hits}/{n_r1} ({r1_rate}%, 95% CI: [{r1_lo}%, {r1_hi}%])")
print(f"Rater 2 (OOP / Class Style): {r2_hits}/{n_r2} ({r2_rate}%, 95% CI: [{r2_lo}%, {r2_hi}%])")
print(f"Overall Rater Detection    : {tot_hits}/{n_total} ({tot_rate}%, 95% CI: [{tot_lo}%, {tot_hi}%])")
print(f"Inter-Rater Outcome Match  : {agreement_count}/{n_r1} ({inter_rater_agreement}%)")

results_payload = {
    'benchmark': 'independent_rater_authored_mutants',
    'freeze_commit': 'a615d1c',
    'total_cases': n_total,
    'rater_1': {'hits': r1_hits, 'total': n_r1, 'recall': r1_rate, 'ci': [r1_lo, r1_hi]},
    'rater_2': {'hits': r2_hits, 'total': n_r2, 'recall': r2_rate, 'ci': [r2_lo, r2_hi]},
    'overall': {'hits': tot_hits, 'total': n_total, 'recall': tot_rate, 'ci': [tot_lo, tot_hi]},
    'inter_rater_agreement_pct': inter_rater_agreement,
    'cases': case_evaluations
}

out_file = os.path.join(RESULTS_DIR, 'rater_authored_mutants_results.json')
with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(results_payload, f, indent=2)

print(f"\n[SUCCESS] Rater mutant evaluation written to {out_file}")

"""
eval/run_held_out_evaluation.py
Step 1: Evaluates the frozen detector suite against the pre-registered held-out taxonomy split (Seed 42).
Design Set:   ['M4', 'M5', 'M7', 'M8', 'M9']
Held-Out Set: ['M1', 'M2', 'M3', 'M6']

Outputs:
    paper_revision/results/held_out_taxonomy_results.json
"""

import json, os, sys, ast
import numpy as np
from scipy import stats

HOSPI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL_DIR = os.path.join(HOSPI, 'eval')
RESULTS_DIR = os.path.join(HOSPI, 'paper_revision', 'results')
os.makedirs(RESULTS_DIR, exist_ok=True)

# Import the frozen detector from eval/run_seeded_defect_evaluation.py
sys.path.insert(0, EVAL_DIR)
from run_seeded_defect_evaluation import (
    wilson_ci, mcnemar_exact, run_live_protocol_check, evaluate_mutant_live,
    PipelineASTAuditor, check_phase1, check_phase2, check_phase3
)

# Load manifests
with open(os.path.join(EVAL_DIR, 'results', 'mutant_manifest.json'), 'r', encoding='utf-8') as f:
    manifest = json.load(f)
valid_mutants = manifest['valid_mutants']

with open(os.path.join(EVAL_DIR, 'results', 'benign_manifest.json'), 'r', encoding='utf-8') as f:
    benign_mutants = json.load(f)

# The pre-registered seed-42 partition
DESIGN_OPS = {'M4', 'M5', 'M7', 'M8', 'M9'}
HELDOUT_OPS = {'M1', 'M2', 'M3', 'M6'}

design_mutants = [m for m in valid_mutants if m['operator'] in DESIGN_OPS]
heldout_mutants = [m for m in valid_mutants if m['operator'] in HELDOUT_OPS]

print(f"Total valid mutants: {len(valid_mutants)}")
print(f"Design set mutants (M4, M5, M7, M8, M9): {len(design_mutants)}")
print(f"Held-out set mutants (M1, M2, M3, M6): {len(heldout_mutants)}")
print(f"Benign controls: {len(benign_mutants)}")

detectors = [
    ('ThreePhaseProtocol', 'expert', 'Our 3-Phase Protocol'),
    ('Phase1', 'expert', 'Phase 1: PSAP Lineage'),
    ('Phase2', 'expert', 'Phase 2: AST-TIV Independence'),
    ('Phase3', 'expert', 'Phase 3: DTEFV Runtime'),
    ('GreatExpectations', 'default', 'Great Expectations (Default)'),
    ('GreatExpectations', 'expert', 'Great Expectations (Expert)'),
    ('EvidentlyAI', 'default', 'Evidently AI (Default)'),
    ('EvidentlyAI', 'expert', 'Evidently AI (Expert)'),
    ('MLflow', 'default', 'MLflow Registry Gates (Default)'),
    ('MLflow', 'expert', 'MLflow Registry Gates (Expert)'),
    ('Deepchecks', 'expert', 'Deepchecks (Expert)'),
    ('YangAST', 'expert', 'Yang et al. ASE 2022 / LeakageDetector')
]

results = {
    'protocol_version': 'HELD_OUT_PROTOCOL_v1.0',
    'master_seed': 42,
    'partition': {
        'design_operators': sorted(list(DESIGN_OPS)),
        'held_out_operators': sorted(list(HELDOUT_OPS)),
        'n_design': len(design_mutants),
        'n_held_out': len(heldout_mutants),
        'n_benign': len(benign_mutants)
    },
    'evaluations': {}
}

# Run evaluations across both sets and benign controls
for det_id, cfg, label in detectors:
    key = f"{det_id}_{cfg}"
    
    # Design set evaluation
    d_hits = [evaluate_mutant_live(m, det_id, cfg) for m in design_mutants]
    d_hit_count = sum(d_hits)
    d_rate, d_low, d_high = wilson_ci(d_hit_count, len(design_mutants))
    
    # Held-out set evaluation
    h_hits = [evaluate_mutant_live(m, det_id, cfg) for m in heldout_mutants]
    h_hit_count = sum(h_hits)
    h_rate, h_low, h_high = wilson_ci(h_hit_count, len(heldout_mutants))
    
    # Benign control evaluation (False Positive Rate)
    b_fps = [evaluate_mutant_live(b, det_id, cfg) for b in benign_mutants]
    b_fp_count = sum(b_fps)
    b_rate, b_low, b_high = wilson_ci(b_fp_count, len(benign_mutants))
    
    # Precision & F1 on held-out set
    tp = h_hit_count
    fp = b_fp_count
    fn = len(heldout_mutants) - h_hit_count
    precision = round(tp / (tp + fp) * 100, 2) if (tp + fp) > 0 else 0.0
    recall = h_rate
    f1 = round(2 * precision * recall / (precision + recall), 2) if (precision + recall) > 0 else 0.0
    
    # Per-operator breakdown on held-out set
    op_breakdown = {}
    for op in sorted(list(HELDOUT_OPS)):
        op_muts = [m for m in heldout_mutants if m['operator'] == op]
        op_h = sum(evaluate_mutant_live(m, det_id, cfg) for m in op_muts)
        r, lo, hi = wilson_ci(op_h, len(op_muts))
        op_breakdown[op] = {'hits': op_h, 'total': len(op_muts), 'recall': r, 'ci': [lo, hi]}
        
    results['evaluations'][key] = {
        'label': label,
        'detector_id': det_id,
        'config': cfg,
        'design_set': {
            'hits': d_hit_count,
            'total': len(design_mutants),
            'recall': d_rate,
            'ci': [d_low, d_high]
        },
        'held_out_set': {
            'hits': h_hit_count,
            'total': len(heldout_mutants),
            'recall': h_rate,
            'ci': [h_low, h_high],
            'precision': precision,
            'f1_score': f1,
            'operator_breakdown': op_breakdown
        },
        'benign_controls': {
            'false_positives': b_fp_count,
            'total': len(benign_mutants),
            'fpr': b_rate,
            'ci': [b_low, b_high],
            'specificity': round(100.0 - b_rate, 2)
        }
    }
    
    print(f"{label:40s} | Design: {d_rate}% [{d_low}, {d_high}] | Held-Out: {h_rate}% [{h_low}, {h_high}] | FPR: {b_rate}%")

# McNemar tests against baselines on Held-Out Set
our_heldout_hits = [evaluate_mutant_live(m, 'ThreePhaseProtocol', 'expert') for m in heldout_mutants]
results['mcnemar_held_out_tests'] = {}

for det_id, cfg, label in detectors:
    if det_id.startswith('Phase') or det_id == 'ThreePhaseProtocol':
        continue
    base_hits = [evaluate_mutant_live(m, det_id, cfg) for m in heldout_mutants]
    mcn = mcnemar_exact(our_heldout_hits, base_hits)
    results['mcnemar_held_out_tests'][f"{det_id}_{cfg}"] = {
        'baseline': label,
        'b_protocol_only': mcn['b'],
        'c_baseline_only': mcn['c'],
        'statistic': mcn['statistic'],
        'p_value': mcn['p_value']
    }

out_path = os.path.join(RESULTS_DIR, 'held_out_taxonomy_results.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)

print(f"\n[SUCCESS] Saved held-out evaluation results to {out_path}")

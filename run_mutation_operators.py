"""
run_mutation_operators.py
Apply M1-M9 mutation operators to HospitalIQ targets.
Uses seeds from EVALUATION_PROTOCOL.md.
"""
import sys, os, json, csv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ml_pipeline', 'mutation_operators'))

from m1_synthetic_tail import M1SyntheticTail
from m2_formula_reconstruction import M2FormulaReconstruction
from m3_contemporaneous_leakage import M3ContemporaneousLeakage
from m4_temporal_shuffle import M4TemporalShuffle
from m5_feature_mismatch import M5FeatureMismatch
from m6_corrupt_metadata import M6CorruptMetadata
from m7_silent_fallback import M7SilentFallback
from m8_ignore_input import M8IgnoreInput
from m9_unmount_route import M9UnmountRoute

HOSPI = os.path.dirname(os.path.abspath(__file__))

# Seeds from EVALUATION_PROTOCOL.md — DO NOT CHANGE
SEEDS = {
    'M1': [6295, 8416, 5696, 5765, 5419, 6697, 6827, 2505, 3271, 1491],
    'M2': [5705, 6851, 7420, 4037, 4265, 1618, 4578, 7248, 4978, 5338],
    'M3': [5683, 1285, 2009, 5545, 5817, 4563, 8558, 1477, 7046, 9645],
    'M4': [6399, 9791, 7437, 1780, 7494, 3877, 9534, 1481, 4895, 9380],
    'M5': [8890, 1748, 1879, 8161, 5754, 1023, 6779, 3620, 6197, 6453],
    'M6': [5748, 1823, 4477, 7124, 5673, 4438, 5286, 7736, 8200, 9600],
    'M7': [2870, 7049, 7573, 1038, 6817, 5851, 3248, 5040, 3478, 4888],
    'M8': [7820, 1978, 8432, 4295, 8731, 2047, 9302, 3871, 4032, 7241],
    'M9': [5847, 7253, 9241, 3847, 8274, 1934, 6219, 4821, 3917, 8534],
}

OPERATORS = {
    'M1': M1SyntheticTail(),
    'M2': M2FormulaReconstruction(),
    'M3': M3ContemporaneousLeakage(),
    'M4': M4TemporalShuffle(),
    'M5': M5FeatureMismatch(),
    'M6': M6CorruptMetadata(),
    'M7': M7SilentFallback(),
    'M8': M8IgnoreInput(),
    'M9': M9UnmountRoute(),
}

TARGETS = {
    'HospitalIQ_forecast': os.path.join(HOSPI, 'ml_pipeline', 'train_forecast.py'),
    'HospitalIQ_scenario': os.path.join(HOSPI, 'ml_pipeline', 'train_scenario.py'),
    'HospitalIQ_main':     os.path.join(HOSPI, 'backend', 'main.py'),
    'Wisconsin_Classifier': os.path.join(HOSPI, 'eval', 'baselines', 'wisconsin_classifier.py'),
    'Empirical_Forecaster': os.path.join(HOSPI, 'eval', 'baselines', 'empirical_forecaster.py'),
}

OUT_DIR = os.path.join(HOSPI, 'eval', 'mutants')
os.makedirs(OUT_DIR, exist_ok=True)
results = []
exclusion_log = []

for op_id, operator in OPERATORS.items():
    for target_name, target_path in TARGETS.items():
        if not os.path.exists(target_path):
            print(f'SKIP {op_id} x {target_name}: file not found')
            continue
        for seed in SEEDS[op_id]:
            out_subdir = os.path.join(OUT_DIR, op_id, target_name)
            res = operator.apply_to_file(target_path, seed, out_subdir)
            res['target'] = target_name
            if res['valid']:
                results.append(res)
                print(f'OK  {op_id} x {target_name} seed={seed}: {res["change_summary"][:60]}')
            else:
                entry = dict(res)
                entry['exclusion_reason'] = res['manifestation_note']
                exclusion_log.append(entry)
                print(f'EX  {op_id} x {target_name} seed={seed}: {res["manifestation_note"][:60]}')

out_path = os.path.join(HOSPI, 'eval', 'results', 'mutant_manifest.json')
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w') as fh:
    json.dump({'valid_mutants': results, 'excluded_mutants': exclusion_log}, fh, indent=2)

excl_path = os.path.join(HOSPI, 'eval', 'results', 'exclusion_log.csv')
with open(excl_path, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['operator', 'target', 'seed', 'exclusion_reason'])
    w.writeheader()
    for row in exclusion_log:
        w.writerow({k: row.get(k, '') for k in ['operator', 'target', 'seed', 'exclusion_reason']})

print(f'\nValid mutants: {len(results)}, Excluded: {len(exclusion_log)}')
print(f'Saved manifest: {out_path}')
print(f'Saved exclusions: {excl_path}')

"""
benign_mutator.py
Generates semantics-preserving benign mutations:
- Adding comments
- Whitespace formatting
- Docstring modifications
- Reordering unused imports
- Local variable renaming (identity preserving)
Used to evaluate false-alarm rates for detectors.
"""
import os, shutil, hashlib, json
import numpy as np

HOSPI = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BENIGN_SEEDS = [
    9384, 7645, 2918, 4572, 1836, 8293, 7462, 9183, 4720, 3847,
    2919, 6745, 1847, 9274, 3618, 8472, 5194, 7382, 2947, 8173,
    4829, 7383, 9473, 1848, 6291, 3841, 8473, 5193, 7384, 2915
]

TARGETS = [
    ('HospitalIQ_forecast', os.path.join(HOSPI, 'ml_pipeline', 'train_forecast.py')),
    ('HospitalIQ_scenario', os.path.join(HOSPI, 'ml_pipeline', 'train_scenario.py')),
    ('HospitalIQ_main', os.path.join(HOSPI, 'backend', 'main.py')),
]

OUT_DIR = os.path.join(HOSPI, 'eval', 'mutants', 'Benign')
os.makedirs(OUT_DIR, exist_ok=True)

benign_manifest = []

for i, seed in enumerate(BENIGN_SEEDS):
    target_name, target_path = TARGETS[i % len(TARGETS)]
    rng = np.random.RandomState(seed)
    with open(target_path, 'r', encoding='utf-8', errors='ignore') as f:
        code = f.read()

    # Mutation styles:
    style = i % 4
    if style == 0:
        mutated = f"# Benign cosmetic comment seed={seed}\n" + code
        summary = f"Prepend cosmetic comment (seed={seed})"
    elif style == 1:
        mutated = code + f"\n# End-of-file diagnostic annotation seed={seed}\n"
        summary = f"Append cosmetic comment (seed={seed})"
    elif style == 2:
        lines = code.split('\n')
        mid = len(lines) // 2
        lines.insert(mid, f"    # [Benign audit marker seed={seed}]")
        mutated = '\n'.join(lines)
        summary = f"Inline cosmetic comment at line {mid} (seed={seed})"
    else:
        # Extra whitespace / docstring update
        mutated = f'"""Benign documentation revision {seed}."""\n' + code
        summary = f"Header docstring addition (seed={seed})"

    out_subdir = os.path.join(OUT_DIR, target_name)
    os.makedirs(out_subdir, exist_ok=True)
    basename = os.path.basename(target_path)
    mutant_path = os.path.join(out_subdir, f"Benign_seed{seed}_{basename}")
    with open(mutant_path, 'w', encoding='utf-8') as f:
        f.write(mutated)

    sha = hashlib.sha256(mutated.encode()).hexdigest()[:16]
    benign_manifest.append({
        'operator': 'Benign',
        'target': target_name,
        'source': target_path,
        'mutant': mutant_path,
        'seed': seed,
        'sha256': sha,
        'valid': True,
        'change_summary': summary
    })

out_json = os.path.join(HOSPI, 'eval', 'results', 'benign_manifest.json')
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(benign_manifest, f, indent=2)

print(f"Generated {len(benign_manifest)} benign control mutants -> {out_json}")

import numpy as np
from base_mutator import BaseMutator

class M5FeatureMismatch(BaseMutator):
    # M5: Drop feature from artifact metadata => predict() shape mismatch
    # Phase that should detect: Phase 3 (DTEFV runtime execution probe)
    def __init__(self): super().__init__('M5')

    def mutate(self, source_code, seed):
        rng = np.random.RandomState(seed)
        drop_idx = int(rng.randint(0, 5))
        tag = f'# [M5 MUTATION seed={seed}]'
        lines = source_code.split('\n')
        snippet = [
            tag,
            'import pickle as _m5p, os as _m5o',
            "_m5f = [f for f in _m5o.listdir('.') if 'metadata' in f and f.endswith('.pkl')]",
            'if _m5f:',
            '    _m5m = _m5p.load(open(_m5f[0], "rb"))',
            '    if isinstance(_m5m, dict) and "feature_cols" in _m5m:',
            f'        if len(_m5m["feature_cols"]) > {drop_idx}:',
            f'            _m5m["feature_cols"].pop({drop_idx})',
            '            _m5p.dump(_m5m, open(_m5f[0], "wb"))',
        ]
        lines = lines[:-3] + snippet + lines[-3:]
        return '\n'.join(lines), f'Dropped feature at index {drop_idx} from metadata'

    def verify(self, mutant_path):
        code = open(mutant_path, encoding='utf-8', errors='ignore').read()
        ok = 'M5 MUTATION' in code and 'feature_cols' in code and '.pop(' in code
        return ok, 'Valid' if ok else 'Mutation not found'

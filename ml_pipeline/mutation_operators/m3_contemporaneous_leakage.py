import numpy as np
from base_mutator import BaseMutator

class M3ContemporaneousLeakage(BaseMutator):
    # M3: Add current-period target mean as a feature
    # Phase that should detect: Phase 2 (PSAP leakage scanner)
    def __init__(self): super().__init__('M3')

    def mutate(self, source_code, seed):
        tag = f'# [M3 MUTATION seed={seed}]'
        lines = source_code.split('\n')
        ins = 0
        for i, l in enumerate(lines):
            if any(k in l for k in ['.fit(', 'train_test_split', 'split_idx']):
                ins = max(0, i - 1); break
        snippet = [
            tag,
            'import numpy as _m3_np',
            '_m3_cmean = y.mean() if hasattr(y, "mean") else float(sum(y)/len(y))',
            'X = _m3_np.column_stack([X, _m3_np.full(len(X), _m3_cmean)])',
            '# feature name: current_period_target_mean (LEAKAGE)',
        ]
        lines = lines[:ins] + snippet + lines[ins:]
        return '\n'.join(lines), 'Appended current-period y.mean() as a feature column'

    def verify(self, mutant_path):
        code = open(mutant_path, encoding='utf-8', errors='ignore').read()
        ok = 'M3 MUTATION' in code and 'y.mean()' in code
        return ok, 'Valid' if ok else 'Mutation not found'

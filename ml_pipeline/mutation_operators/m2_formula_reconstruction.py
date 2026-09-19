import numpy as np
from base_mutator import BaseMutator

class M2FormulaReconstruction(BaseMutator):
    # M2: Replace training target with deterministic function of inputs
    # Phase that should detect: Phase 2 (PSAP AST target-independence check)
    def __init__(self): super().__init__('M2')

    def mutate(self, source_code, seed):
        rng = np.random.RandomState(seed)
        c1 = round(float(rng.uniform(1.5, 4.0)), 3)
        c2 = int(rng.randint(50, 500))
        tag = f'# [M2 MUTATION seed={seed}]'
        lines = source_code.split('\n')
        ins = 0
        for i, l in enumerate(lines):
            if any(k in l for k in ['.fit(', 'y_train', 'fit(X']):
                ins = max(0, i - 1); break
        snippet = [
            tag,
            f'# target y replaced with deterministic formula of X[:,0]',
            f'y = X[:, 0] * {c1} + {c2}',
        ]
        lines = lines[:ins] + snippet + lines[ins:]
        return '\n'.join(lines), f'Target y = X[:,0]*{c1}+{c2} (R2~1.0 by construction)'

    def verify(self, mutant_path):
        code = open(mutant_path, encoding='utf-8', errors='ignore').read()
        ok = 'M2 MUTATION' in code and 'X[:, 0]' in code
        return ok, 'Valid' if ok else 'Mutation not found'

import numpy as np
from base_mutator import BaseMutator

class M8IgnoreInput(BaseMutator):
    # M8: Replace feature with constant at inference time
    # Phase that should detect: Phase 3 (DTEFV feature-sensitivity probe)
    def __init__(self): super().__init__('M8')

    def mutate(self, source_code, seed):
        rng = np.random.RandomState(seed)
        fi = int(rng.randint(0, 5))
        cv = round(float(rng.uniform(0, 1)), 4)
        tag = f'# [M8 MUTATION seed={seed}]'
        lines = source_code.split('\n')
        ins = 0
        for i, l in enumerate(lines):
            if any(k in l for k in ['joblib.dump', 'pickle.dump']):
                ins = max(0, i - 1); break
        snippet = [
            tag,
            '_m8orig = model.predict',
            'def _m8pred(X):',
            '    import numpy as _m8n',
            '    Xc = _m8n.array(X, copy=True)',
            f'    Xc[:, {fi}] = {cv}',
            '    return _m8orig(Xc)',
            'model.predict = _m8pred',
        ]
        lines = lines[:ins] + snippet + lines[ins:]
        return '\n'.join(lines), f'Feature index {fi} replaced with constant {cv} at inference'

    def verify(self, mutant_path):
        code = open(mutant_path, encoding='utf-8', errors='ignore').read()
        ok = 'M8 MUTATION' in code and '_m8pred' in code
        return ok, 'Valid' if ok else 'Mutation not found'

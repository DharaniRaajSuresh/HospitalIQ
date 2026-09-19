import numpy as np
from base_mutator import BaseMutator

class M7SilentFallback(BaseMutator):
    # M7: Wrap predict() returning constant on any exception
    # Phase that should detect: Phase 3 (DTEFV silent-fallback probe)
    def __init__(self): super().__init__('M7')

    def mutate(self, source_code, seed):
        rng = np.random.RandomState(seed)
        fv = round(float(rng.uniform(0, 100)), 2)
        tag = f'# [M7 MUTATION seed={seed}]'
        lines = source_code.split('\n')
        ins = 0
        for i, l in enumerate(lines):
            if any(k in l for k in ['joblib.dump', 'pickle.dump', 'save_model']):
                ins = max(0, i - 1); break
        snippet = [
            tag,
            '_m7orig = model.predict',
            'def _m7safe(X):',
            '    try: return _m7orig(X)',
            '    except Exception:',
            '        import numpy as _m7n',
            f'        return _m7n.full(len(X), {fv})',
            'model.predict = _m7safe',
        ]
        lines = lines[:ins] + snippet + lines[ins:]
        return '\n'.join(lines), f'Wrapped model.predict() returning constant {fv} on exception'

    def verify(self, mutant_path):
        code = open(mutant_path, encoding='utf-8', errors='ignore').read()
        ok = 'M7 MUTATION' in code and '_m7safe' in code
        return ok, 'Valid' if ok else 'Mutation not found'

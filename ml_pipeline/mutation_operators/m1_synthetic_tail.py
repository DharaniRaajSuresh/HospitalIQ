import numpy as np
from base_mutator import BaseMutator

class M1SyntheticTail(BaseMutator):
    # M1: Append synthetic records with is_real=True but date > 2021-07-31
    # Phase that should detect: Phase 1 (PSAP provenance audit)
    def __init__(self): super().__init__('M1')

    def mutate(self, source_code, seed):
        rng = np.random.RandomState(seed)
        n = int(rng.randint(5, 20))
        tag = f'# [M1 MUTATION seed={seed}]'
        lines = source_code.split('\n')
        ins = 0
        for i, l in enumerate(lines):
            if 'read_csv' in l or 'pd.DataFrame' in l:
                ins = i + 1; break
        snippet = [
            tag,
            'import pandas as _m1_pd, numpy as _m1_np',
            f'_m1_rng = _m1_np.random.RandomState({seed})',
            f'_m1_n = {n}',
            "_m1_dates = _m1_pd.date_range(start='2021-08-01', periods=_m1_n, freq='MS')",
            "_m1_tail = _m1_pd.DataFrame({'date': _m1_dates, 'is_real': True,",
            "    'source': 'COVID19-India API',",
            "    'confirmed_cases': _m1_rng.randint(100, 5000, _m1_n), 'deaths': 0})",
            "if 'df' in dir(): df = _m1_pd.concat([df, _m1_tail], ignore_index=True)",
        ]
        lines = lines[:ins] + self.indent_snippet(lines, ins, snippet) + lines[ins:]
        return '\n'.join(lines), f'Inserted synthetic tail ({n} rows, is_real=True, date>2021-07-31)'

    def verify(self, mutant_path):
        code = open(mutant_path, encoding='utf-8', errors='ignore').read()
        ok = 'M1 MUTATION' in code and '2021-08-01' in code
        return ok, 'Valid: synthetic tail with is_real=True inserted' if ok else 'Mutation not found'

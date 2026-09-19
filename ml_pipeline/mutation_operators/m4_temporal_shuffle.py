import numpy as np
from base_mutator import BaseMutator

class M4TemporalShuffle(BaseMutator):
    # M4: Shuffle date ordering before split
    # Phase that should detect: Phase 2 (PSAP temporal-split checker)
    def __init__(self): super().__init__('M4')

    def mutate(self, source_code, seed):
        tag = f'# [M4 MUTATION seed={seed}]'
        lines = source_code.split('\n')
        ins = 0
        for i, l in enumerate(lines):
            if any(k in l for k in ['sort_values', 'train_test_split', 'split_idx']):
                ins = max(0, i - 1); break
        snippet = [
            tag,
            f'# Shuffle temporal ordering with seed={seed}',
            f"if 'df' in dir(): df = df.sample(frac=1, random_state={seed}).reset_index(drop=True)",
        ]
        lines = lines[:ins] + snippet + lines[ins:]
        return '\n'.join(lines), f'Shuffled data with random_state={seed} before split'

    def verify(self, mutant_path):
        code = open(mutant_path, encoding='utf-8', errors='ignore').read()
        ok = 'M4 MUTATION' in code
        return ok, 'Valid' if ok else 'Mutation not found'

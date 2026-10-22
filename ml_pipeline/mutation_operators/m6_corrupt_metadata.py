from base_mutator import BaseMutator

class M6CorruptMetadata(BaseMutator):
    # M6: Convert metadata dict to list so .get() raises AttributeError
    # Phase that should detect: Phase 3 (DTEFV artifact-load probe)
    def __init__(self): super().__init__('M6')

    def mutate(self, source_code, seed):
        tag = f'# [M6 MUTATION seed={seed}]'
        lines = source_code.split('\n')
        snippet = [
            tag,
            'import pickle as _m6p, os as _m6o',
            "_m6f = [f for f in _m6o.listdir('.') if 'metadata' in f and f.endswith('.pkl')]",
            'if _m6f:',
            '    _m6m = _m6p.load(open(_m6f[0], "rb"))',
            '    if isinstance(_m6m, dict):',
            '        _m6p.dump(list(_m6m.items()), open(_m6f[0], "wb"))',
        ]
        lines = lines + [''] + snippet
        return '\n'.join(lines), 'Converted metadata dict to list'

    def verify(self, mutant_path):
        code = open(mutant_path, encoding='utf-8', errors='ignore').read()
        ok = 'M6 MUTATION' in code and 'list(_m6m.items())' in code
        return ok, 'Valid' if ok else 'Mutation not found'

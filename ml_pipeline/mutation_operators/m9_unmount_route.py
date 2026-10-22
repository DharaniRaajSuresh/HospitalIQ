from base_mutator import BaseMutator

class M9UnmountRoute(BaseMutator):
    # M9: Comment out audit route registration so GET /audit returns 404
    # Phase that should detect: Phase 2 (code structure) or Phase 3
    def __init__(self): super().__init__('M9')

    def mutate(self, source_code, seed):
        lines = source_code.split('\n')
        removed = []
        for i, l in enumerate(lines):
            if 'include_router' in l and 'audit' in l.lower():
                lines[i] = f'# [M9 MUTATION seed={seed}] REMOVED: ' + l
                removed.append(l.strip())
                break
        summary = f'Commented out: {removed}' if removed else 'No audit route found'
        return '\n'.join(lines), summary

    def verify(self, mutant_path):
        code = open(mutant_path, encoding='utf-8', errors='ignore').read()
        ok = 'M9 MUTATION' in code
        return ok, 'Valid' if ok else 'No audit route to remove in this file'

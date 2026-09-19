import abc, os, shutil, hashlib, ast

class BaseMutator(abc.ABC):
    def __init__(self, operator_id):
        self.operator_id = operator_id

    @staticmethod
    def indent_snippet(lines, ins, snippet):
        indent = ""
        search_range = list(range(ins, min(len(lines), ins + 10))) + list(range(ins - 1, max(-1, ins - 10), -1))
        for idx in search_range:
            if 0 <= idx < len(lines):
                line = lines[idx]
                if line.strip() and not line.strip().startswith('#'):
                    indent = line[:len(line) - len(line.lstrip())]
                    break
        return [indent + s if s.strip() else "" for s in snippet]

    def apply_to_file(self, source_path, seed, out_dir):
        os.makedirs(out_dir, exist_ok=True)
        basename = os.path.basename(source_path)
        mutant_path = os.path.join(out_dir, f'{self.operator_id}_seed{seed}_{basename}')
        shutil.copy2(source_path, mutant_path)
        with open(mutant_path, encoding='utf-8', errors='ignore') as fh:
            original = fh.read()
        mutated, summary = self.mutate(original, seed)
        with open(mutant_path, 'w', encoding='utf-8') as fh:
            fh.write(mutated)
        valid, note = self.verify(mutant_path)
        # Verify valid Python AST syntax
        try:
            ast.parse(mutated)
        except Exception as e:
            valid = False
            note = f"Invalid Python syntax: {type(e).__name__} ({str(e)})"

        sha = hashlib.sha256(mutated.encode()).hexdigest()[:16]
        return {
            'operator': self.operator_id, 'source': source_path,
            'mutant': mutant_path, 'seed': seed, 'sha256': sha,
            'valid': valid, 'manifestation_note': note, 'change_summary': summary,
        }

    @abc.abstractmethod
    def mutate(self, source_code, seed): pass

    @abc.abstractmethod
    def verify(self, mutant_path): pass


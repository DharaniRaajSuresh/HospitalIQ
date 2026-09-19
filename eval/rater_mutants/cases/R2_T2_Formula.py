# Rater 2 - Tier 2: Formulation: Synthetic target built from polynomial feature combinations
# Style: Class method vector math
class SyntheticDatasetGenerator:
    def generate(self, X):
        target = X[:, 0] * 1.8 + X[:, 2] * 0.4
        return target

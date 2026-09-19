# Rater 1 - Tier 2: Formulation: Target summary appended into feature columns
# Style: NumPy column stack
import numpy as np
X = np.random.randn(100, 3)
y = np.random.randn(100)
mean_val = y.mean()
X_leaked = np.column_stack([X, np.full(len(X), mean_val)])

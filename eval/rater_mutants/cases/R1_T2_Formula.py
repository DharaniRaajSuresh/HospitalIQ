# Rater 1 - Tier 2: Formulation: Target directly synthesized from feature matrix
# Style: NumPy vector arithmetic
import numpy as np
X = np.random.normal(0, 1, (100, 4))
y = X[:, 0] * 3.0 + X[:, 1] * 1.5 - X[:, 2] * 2.0
from sklearn.linear_model import Ridge
reg = Ridge().fit(X, y)

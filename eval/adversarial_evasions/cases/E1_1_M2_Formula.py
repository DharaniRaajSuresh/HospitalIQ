# Adversarial Case: E1_1 - Single-file algebraic formula
# Intended Mechanism: Explicit algebraic formula in same file
import numpy as np
X = np.random.randn(100, 5)
# Deterministic linear formula
y = X[:, 0] * 2.5 + X[:, 1] * 1.2 - X[:, 2] * 0.8
from sklearn.ensemble import RandomForestRegressor
model = RandomForestRegressor().fit(X, y)

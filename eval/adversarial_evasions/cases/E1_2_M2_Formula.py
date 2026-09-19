# Adversarial Case: E1_2 - Cross-module helper delegation
# Intended Mechanism: Formula computation delegated to imported external module
import numpy as np
from external_math_helper import compute_deterministic_target
X = np.random.randn(100, 5)
y = compute_deterministic_target(X)
from sklearn.ensemble import RandomForestRegressor
model = RandomForestRegressor().fit(X, y)

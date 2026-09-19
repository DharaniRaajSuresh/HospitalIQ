# Adversarial Case: E1_3 - Matrix dot product intrinsic
# Intended Mechanism: Target computed via np.dot matrix intrinsic without explicit binary arithmetic operators
import numpy as np
X = np.random.randn(100, 5)
weights = np.array([2.5, 1.2, -0.8, 0.4, 1.1])
# Linear formula via matrix multiplication
y = np.dot(X, weights)
from sklearn.ensemble import RandomForestRegressor
model = RandomForestRegressor().fit(X, y)

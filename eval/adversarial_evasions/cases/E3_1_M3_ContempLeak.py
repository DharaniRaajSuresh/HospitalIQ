# Adversarial Case: E3_1 - Direct column concatenation leakage
# Intended Mechanism: Direct concatenation of target mean or same-period target
import numpy as np
X = np.random.randn(100, 3)
y = np.random.randn(100)
y_mean = y.mean()
X_leaked = np.column_stack([X, np.full(len(X), y_mean)])

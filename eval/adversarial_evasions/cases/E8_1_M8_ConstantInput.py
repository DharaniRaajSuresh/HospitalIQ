# Adversarial Case: E8_1 - Feature column overwrite with constant
# Intended Mechanism: Feature column overwritten with constant 0.0 before predict
import numpy as np
X = np.random.randn(10, 5)
X[:, 3] = 0.0 # Feature overwritten with constant
model.predict(X)

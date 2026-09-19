# Adversarial Case: E8_2 - Dead-code feature assignment
# Intended Mechanism: Feature passed to dead-code branch; active execution feeds constant
import numpy as np
X = np.random.randn(10, 5)
if False:
    y = model.predict(X)
else:
    X_fixed = X.copy()
    X_fixed[:, 2] = 100.0 # Feature ignored
    y = model.predict(X_fixed)

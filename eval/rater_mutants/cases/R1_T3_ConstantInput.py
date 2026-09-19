# Rater 1 - Tier 3: Deployment: Feature column overwritten with constant scalar
# Style: Array slicing assign
import numpy as np
X = np.random.randn(20, 4)
X[:, 1] = 0.0 # Feature zeroed out
model.predict(X)

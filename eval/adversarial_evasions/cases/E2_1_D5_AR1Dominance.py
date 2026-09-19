# Adversarial Case: E2_1 - Collinear noisy decoy dilution
# Intended Mechanism: Two collinear noisy lag copies added to dilute primary lag-1 tree gain below tau_AR = 0.50
import numpy as np
import pandas as pd
# Decoy feature dilution: lag-1 gain split with collinear decoy
lag1 = np.random.randn(100)
decoy1 = lag1 + np.random.normal(0, 0.05, 100)
decoy2 = lag1 + np.random.normal(0, 0.08, 100)
# Feature importance will be shared across lag1, decoy1, decoy2

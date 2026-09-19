# Adversarial Case: E5_3 - Silent numpy rank broadcast
# Intended Mechanism: Numpy broadcasting reshapes 1D tensor to 2D matching rank but misaligning features
import numpy as np
# 1D array broadcasted via newaxis, bypassing rank check
x_raw = np.array([1.0, 2.0, 3.0])
x_broadcast = x_raw[:, np.newaxis].T # Shape (1, 3) satisfies 2D rank

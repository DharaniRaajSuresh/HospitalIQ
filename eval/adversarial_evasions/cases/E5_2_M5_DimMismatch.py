# Adversarial Case: E5_2 - Dynamic kwargs unpacking
# Intended Mechanism: Inference feeds dynamic dictionary unpacking into predict
import numpy as np
class MockModel:
    n_features_in_ = 5
    def predict(self, X):
        if X.shape[1] != self.n_features_in_: raise ValueError("Dim mismatch")
        return [1.0]
model = MockModel()
kwargs = {'a': 1, 'b': 2, 'c': 3} # Only 3 features provided
model.predict(np.array(list(kwargs.values())).reshape(1, -1))

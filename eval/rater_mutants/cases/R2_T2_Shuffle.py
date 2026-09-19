# Rater 2 - Tier 2: Formulation: Index random permutation prior to temporal splitting
# Style: NumPy permutation
import numpy as np
class TimeSeriesSplitter:
    def split(self, data):
        indices = np.random.permutation(len(data))
        return data[indices]

# Adversarial Case: E2_3 - Direct autoregressive dominance
# Intended Mechanism: Unmitigated lag-1 dominance with 82% gain share
import pandas as pd
df = pd.DataFrame({'lag_1_cases': [10, 20, 30], 'y': [11, 21, 31]})
# 82% gain on lag_1_cases

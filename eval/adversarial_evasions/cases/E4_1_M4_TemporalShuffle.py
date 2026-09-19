# Adversarial Case: E4_1 - In-place sample shuffling
# Intended Mechanism: Explicit df.sample(frac=1.0) on time series
import pandas as pd
df = pd.DataFrame({'date': pd.date_range('2021-01-01', periods=100), 'y': range(100)})
df = df.sample(frac=1.0) # Non-chronological shuffle

# Adversarial Case: E4_2 - Permutation index shuffling
# Intended Mechanism: Permutation applied to index prior to train/test split
import numpy as np, pandas as pd
df = pd.DataFrame({'date': pd.date_range('2021-01-01', periods=100), 'y': range(100)})
df = df.iloc[np.random.permutation(len(df))]

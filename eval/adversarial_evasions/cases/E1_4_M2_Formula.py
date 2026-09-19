# Adversarial Case: E1_4 - DataFrame lambda abstraction
# Intended Mechanism: Target generated via row-wise lambda inside DataFrame.apply()
import pandas as pd
import numpy as np
df = pd.DataFrame(np.random.randn(100, 5), columns=['f1', 'f2', 'f3', 'f4', 'f5'])
df['target'] = df.apply(lambda row: row['f1'] * 2.0 + row['f2'] * 1.5, axis=1)
from sklearn.ensemble import RandomForestRegressor
model = RandomForestRegressor().fit(df[['f1','f2','f3','f4','f5']], df['target'])

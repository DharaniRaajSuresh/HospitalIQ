# Adversarial Case: E3_2 - Indirect dictionary lookup join
# Intended Mechanism: Same-period target statistics mapped through intermediate dictionary table
import pandas as pd, numpy as np
df = pd.DataFrame({'date': ['2021-05-01']*100, 'cases': np.random.randn(100)})
summary_map = dict(df.groupby('date')['cases'].mean())
# Indirect join via map
df['leak_feat'] = df['date'].map(summary_map)

# Rater 2 - Tier 2: Formulation: Target summary concatenated via Pandas concat
# Style: Pandas DataFrame concat
import pandas as pd
df_features = pd.DataFrame({'a': [1,2,3]})
y = pd.Series([10, 20, 30])
y_mean = y.mean()
df_features = pd.concat([df_features, pd.Series([y_mean]*3, name='leak')], axis=1)

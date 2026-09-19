# Adversarial Case: E3_4 - Multi-step dataframe relational merge
# Intended Mechanism: Leaked target aggregate merged through intermediate multi-key dataframe merge
import pandas as pd
df_raw = pd.DataFrame({'state': ['MH']*10, 'date': ['2021-05']*10, 'deaths': [5]*10})
agg = df_raw.groupby(['state', 'date'])['deaths'].sum().reset_index()
merged = pd.merge(df_raw, agg, on=['state', 'date'], suffixes=('', '_contemp'))

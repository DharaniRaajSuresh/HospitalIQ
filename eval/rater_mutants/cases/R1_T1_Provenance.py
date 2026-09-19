# Rater 1 - Tier 1: Provenance: Synthetic records appended with real flag
# Style: Functional procedural script
import pandas as pd
real_df = pd.read_csv('surveillance.csv')
synthetic_tail = pd.DataFrame({'cases': [500]*50, 'is_real': [True]*50, 'date': ['2021-10-31']*50})
df = pd.concat([real_df, synthetic_tail])

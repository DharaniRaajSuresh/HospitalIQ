# Rater 1 - Tier 2: Formulation: Dataframe sampled non-chronologically
# Style: Pandas sample
import pandas as pd
df = pd.DataFrame({'time': range(100), 'val': range(100)})
df_shuffled = df.sample(frac=1.0)

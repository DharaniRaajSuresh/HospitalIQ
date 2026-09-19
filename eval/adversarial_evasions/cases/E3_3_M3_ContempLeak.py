# Adversarial Case: E3_3 - Center-aligned rolling lookahead
# Intended Mechanism: Rolling average window with center=True incorporating future observations
import pandas as pd
df = pd.DataFrame({'cases': [1, 2, 3, 4, 5]})
# center=True looks ahead into future timesteps
df['cases_smooth'] = df['cases'].rolling(3, center=True).mean()

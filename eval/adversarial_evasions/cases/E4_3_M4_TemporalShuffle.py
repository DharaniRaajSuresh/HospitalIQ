# Adversarial Case: E4_3 - Date format string inversion
# Intended Mechanism: Month/day swap during date parsing causing scrambled temporal sorting without explicit shuffle
import pandas as pd
# Date format parsing with dayfirst=True on MM/DD strings inverts order
dates = ['05/01/2021', '05/02/2021', '05/13/2021', '06/01/2021']
parsed = pd.to_datetime(dates, format='mixed', dayfirst=True)
df = pd.DataFrame({'date': parsed, 'cases': [10, 20, 30, 40]}).sort_values('date')

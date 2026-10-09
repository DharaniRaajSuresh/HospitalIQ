import os, sys, io, sqlite3
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

con = sqlite3.connect('ml_pipeline/data/hospitaliq.db')
df_db = pd.read_sql("SELECT disease, state, district, year, month, confirmed_cases, deaths FROM pandemic_outbreak WHERE disease = 'COVID-19' AND state = 'Maharashtra'", con)
print("Maharashtra rows in hospitaliq.db:", len(df_db))
print(df_db.head(10))

# Group by year and month
monthly_db = df_db.groupby(['year', 'month'])[['confirmed_cases', 'deaths']].sum().reset_index()
print("\nMonthly totals for Maharashtra in hospitaliq.db:")
print(monthly_db.head(20).to_string())

# Now inspect outbreak_real.csv
df_real = pd.read_csv('ml_pipeline/data/raw/outbreak_real.csv')
mh_real = df_real[(df_real['disease'] == 'COVID-19') & (df_real['state'] == 'Maharashtra')].sort_values('date')
print("\nMonthly totals for Maharashtra in outbreak_real.csv:")
print(mh_real.head(20)[['date', 'confirmed_cases', 'deaths', 'source', 'is_real']].to_string())

import sys, os, pickle, math
import pandas as pd
import numpy as np

# Set project root
HOSPI = os.path.abspath('.')
sys.path.insert(0, HOSPI)

from backend.predictors.forecast_predictor import ForecastPredictor

predictor = ForecastPredictor()
predictor.load_model()

# Load raw outbreak data
df = pd.read_csv('ml_pipeline/data/raw/outbreak_real.csv')
covid = df[df['disease'] == 'COVID-19'].sort_values(['state', 'date']).reset_index(drop=True)

# Test across multiple states for April, May, June, July 2021
meta = pickle.load(open('ml_pipeline/data/models/forecast_metadata.pkl', 'rb'))
model_cases = pickle.load(open('ml_pipeline/data/models/forecast_cases_model.pkl', 'rb'))

test_states = ['Maharashtra', 'Uttar Pradesh', 'Karnataka', 'Delhi', 'Tamil Nadu']
dates = ['2021-04-01', '2021-05-01', '2021-06-01', '2021-07-01']

results = []

for state in test_states:
    sdf = covid[covid['state'] == state].sort_values('date').reset_index(drop=True)
    for target_date in dates:
        dt = pd.to_datetime(target_date)
        # Find index of target_date
        match = sdf[sdf['date'] == target_date]
        if match.empty:
            continue
        idx = match.index[0]
        if idx < 3:
            continue
        
        # History is prior 3 entries
        h_entries = sdf.iloc[idx-3:idx]
        history = [(int(r['confirmed_cases']), int(r['deaths'])) for _, r in h_entries.iterrows()]
        
        # Call production predictor
        input_payload = {
            'disease': 'COVID-19',
            'state': state,
            'history': history,
            'months_ahead': 1,
            'start_year_month': [dt.year, dt.month - 1 if dt.month > 1 else 12]
        }
        res = predictor.predict(input_payload)
        prod_pred = res['forecast'][0]['confirmed_cases']
        
        # Direct calculation using training feature-building logic
        lag1_c, lag2_c, lag3_c = history[-1][0], history[-2][0], history[-3][0]
        lag1_d, lag2_d = history[-1][1], history[-2][1]
        m = dt.month
        y = dt.year
        m_sin = math.sin(2 * math.pi * m / 12)
        m_cos = math.cos(2 * math.pi * m / 12)
        y_norm = (y - 2017) / 15
        ma3 = (lag1_c + lag2_c + lag3_c) / 3
        growth = (lag1_c - lag2_c) / max(lag2_c, 1)
        dp = meta.get('disease_params', {}).get('COVID-19', {'cfr': 0.05, 'r0': 1.5})
        cap = meta.get('state_beds', {}).get(state, {'total_beds': 1000, 'hospitals': 10})

        feat_direct = {
            'month_sin': m_sin, 'month_cos': m_cos, 'year_normalized': y_norm,
            'lag_1_cases': lag1_c, 'lag_2_cases': lag2_c, 'lag_3_cases': lag3_c,
            'lag_1_deaths': lag1_d, 'lag_2_deaths': lag2_d,
            'cases_ma3': ma3, 'cases_growth': growth,
            'disease_cfr': dp.get('cfr', 0), 'disease_r0': dp.get('r0', 0),
            'state_beds': cap.get('total_beds', 1000) if isinstance(cap, dict) else 1000,
            'state_hospitals': cap.get('hospitals', 10) if isinstance(cap, dict) else 10,
            'disease_enc': meta['disease_encoding']['COVID-19'],
            'state_enc': meta['state_encoding'][state]
        }
        X_vec = np.array([[feat_direct[c] for c in meta['feature_cols']]])
        direct_pred = float(np.expm1(model_cases.predict(X_vec)[0]))
        
        actual_val = int(match.iloc[0]['confirmed_cases'])
        results.append({
            'state': state, 'date': target_date, 'actual': actual_val,
            'prod_pred': prod_pred, 'direct_pred': round(direct_pred, 1),
            'diff': abs(prod_pred - round(direct_pred))
        })

res_df = pd.DataFrame(results)
print("Comparison of Production Predictor vs Direct Model on Delta Windows:")
print(res_df.to_string())
print(f"\nMax difference between Production Predictor and Direct Model: {res_df['diff'].max()} (rounding error)")

import numpy as np
import pandas as pd
import math
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_percentage_error, r2_score
from statsmodels.tsa.api import SimpleExpSmoothing, Holt

def compute_wape(y_true, y_pred):
    denom = np.sum(y_true)
    if denom == 0:
        return 0.0
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0)

df = pd.read_csv('ml_pipeline/data/raw/outbreak_real.csv')
cov = df[df['disease'] == 'COVID-19'].copy()
cov['date'] = pd.to_datetime(cov['date'])
cov = cov.sort_values(['state', 'date']).reset_index(drop=True)
real_cov = cov[cov['date'] <= '2021-07-31'].copy()

# Build features and time-series
records = []
for state, group in real_cov.groupby('state'):
    g = group.sort_values('date').reset_index(drop=True)
    if len(g) < 4: continue
    for i in range(3, len(g)):
        row = g.iloc[i]
        lag1 = g.iloc[i-1]
        lag2 = g.iloc[i-2]
        lag3 = g.iloc[i-3]
        # Check for lag 12 (seasonal)
        lag12_val = g.iloc[i-12]['confirmed_cases'] if i >= 12 else lag1['confirmed_cases']
        m = row['date'].month
        records.append({
            'state': state,
            'date': str(row['date'].date()),
            'month': m,
            'month_sin': math.sin(2 * math.pi * m / 12),
            'month_cos': math.cos(2 * math.pi * m / 12),
            'lag_1_cases': float(lag1['confirmed_cases']),
            'lag_2_cases': float(lag2['confirmed_cases']),
            'lag_3_cases': float(lag3['confirmed_cases']),
            'lag_12_cases': float(lag12_val),
            'cases_ma3': float((lag1['confirmed_cases'] + lag2['confirmed_cases'] + lag3['confirmed_cases']) / 3.0),
            'lag_1_diff': float(lag1['confirmed_cases'] - lag2['confirmed_cases']),
            'lag_2_diff': float(lag2['confirmed_cases'] - lag3['confirmed_cases']),
            'target_cases': float(row['confirmed_cases']),
            'target_diff': float(row['confirmed_cases'] - lag1['confirmed_cases']),
        })
real_features = pd.DataFrame(records)
train_real = real_features[real_features['date'] < '2021-04-01'].copy()
test_real = real_features[real_features['date'] >= '2021-04-01'].copy()

y_test = test_real['target_cases'].values
lag1_test = test_real['lag_1_cases'].values

# 1. Seasonal Naive (lag 12)
pred_snaive = test_real['lag_12_cases'].values
wape_snaive = compute_wape(y_test, pred_snaive)
mape_snaive = float(mean_absolute_percentage_error(y_test, np.maximum(pred_snaive, 1)) * 100)
r2_snaive = float(r2_score(y_test, pred_snaive))
print(f'Seasonal Naive (lag-12): WAPE={wape_snaive:.2f}%, MAPE={mape_snaive:.2f}%, R2={r2_snaive:.4f}')

# 2. ETS (Holt's Exponential Smoothing per state fit on train_real)
ets_preds = []
for idx, row in test_real.iterrows():
    st = row['state']
    history = train_real[train_real['state'] == st]['target_cases'].values
    if len(history) >= 4:
        try:
            fit = Holt(history, initialization_method='estimated').fit()
            pred = max(0, fit.forecast(1)[0])
        except:
            pred = history[-1]
    else:
        pred = row['lag_1_cases']
    ets_preds.append(pred)
ets_preds = np.array(ets_preds)
wape_ets = compute_wape(y_test, ets_preds)
mape_ets = float(mean_absolute_percentage_error(y_test, np.maximum(ets_preds, 1)) * 100)
r2_ets = float(r2_score(y_test, ets_preds))
print(f'ETS (Exponential Smoothing): WAPE={wape_ets:.2f}%, MAPE={mape_ets:.2f}%, R2={r2_ets:.4f}')

# 3. Grid-tuned XGBoost on Wave-1 VALIDATION ONLY (train < 2021-01-01, val 2021-01 to 2021-03)
val_mask = train_real['date'] >= '2021-01-01'
tr_sub = train_real[~val_mask]
val_sub = train_real[val_mask]
diff_features = ['month_sin', 'month_cos', 'lag_1_diff', 'lag_2_diff', 'cases_ma3']

best_wape = 999.0
best_params = {}
for depth in [2, 3, 4]:
    for lr in [0.01, 0.03, 0.05, 0.1]:
        for n_est in [30, 50, 100]:
            for reg in [0.1, 1.0, 5.0]:
                m = XGBRegressor(max_depth=depth, learning_rate=lr, n_estimators=n_est, reg_lambda=reg, random_state=42)
                m.fit(tr_sub[diff_features], tr_sub['target_diff'])
                p_diff = m.predict(val_sub[diff_features])
                p = np.maximum(0, val_sub['lag_1_cases'].values + p_diff)
                w = compute_wape(val_sub['target_cases'].values, p)
                if w < best_wape:
                    best_wape = w
                    best_params = {'max_depth': depth, 'learning_rate': lr, 'n_estimators': n_est, 'reg_lambda': reg}

print('Best params tuned on Wave-1 validation:', best_params, f'Validation WAPE: {best_wape:.2f}%')
xgb_tuned = XGBRegressor(**best_params, random_state=42)
xgb_tuned.fit(train_real[diff_features], train_real['target_diff'])
pred_tuned = np.maximum(0, lag1_test + xgb_tuned.predict(test_real[diff_features]))
wape_tuned = compute_wape(y_test, pred_tuned)
mape_tuned = float(mean_absolute_percentage_error(y_test, pred_tuned) * 100)
r2_tuned = float(r2_score(y_test, pred_tuned))
print(f'Tuned XGBoost (Wave-1 CV tuned): WAPE={wape_tuned:.2f}%, MAPE={mape_tuned:.2f}%, R2={r2_tuned:.4f}')

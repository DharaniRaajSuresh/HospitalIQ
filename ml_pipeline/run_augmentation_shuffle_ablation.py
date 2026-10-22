import os
import json
import math
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_percentage_error, r2_score

def compute_wape(y_true, y_pred):
    denom = np.sum(y_true)
    if denom == 0:
        return 0.0
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0)

def main():
    print('='*70)
    print('AUGMENTATION ABLATION: SYNTHETIC TARGET SHUFFLE EXPERIMENT (rho=0.50)')
    print('='*70)

    df = pd.read_csv('ml_pipeline/data/raw/outbreak_real.csv')
    cov = df[df['disease'] == 'COVID-19'].copy()
    cov['date'] = pd.to_datetime(cov['date'])
    cov = cov.sort_values(['state', 'date']).reset_index(drop=True)

    real_cov = cov[cov['date'] <= '2021-07-31'].copy()
    synth_cov = cov[cov['date'] > '2021-07-31'].copy()

    def build_dataset(data_source):
        records = []
        for state, group in data_source.groupby('state'):
            g = group.sort_values('date').reset_index(drop=True)
            if len(g) < 4: continue
            for i in range(3, len(g)):
                row = g.iloc[i]
                lag1 = g.iloc[i-1]
                lag2 = g.iloc[i-2]
                lag3 = g.iloc[i-3]
                m = row['date'].month
                records.append({
                    'date': str(row['date'].date()),
                    'state': state,
                    'month_sin': math.sin(2 * math.pi * m / 12),
                    'month_cos': math.cos(2 * math.pi * m / 12),
                    'lag_1_cases': float(lag1['confirmed_cases']),
                    'lag_2_cases': float(lag2['confirmed_cases']),
                    'lag_3_cases': float(lag3['confirmed_cases']),
                    'cases_ma3': float((lag1['confirmed_cases'] + lag2['confirmed_cases'] + lag3['confirmed_cases']) / 3.0),
                    'lag_1_diff': float(lag1['confirmed_cases'] - lag2['confirmed_cases']),
                    'lag_2_diff': float(lag2['confirmed_cases'] - lag3['confirmed_cases']),
                    'target_cases': float(row['confirmed_cases']),
                    'target_diff': float(row['confirmed_cases'] - lag1['confirmed_cases']),
                })
        return pd.DataFrame(records)

    real_features = build_dataset(real_cov)
    synth_features = build_dataset(synth_cov)

    train_real = real_features[real_features['date'] < '2021-04-01'].copy()
    test_real = real_features[real_features['date'] >= '2021-04-01'].copy()

    diff_features = ['month_sin', 'month_cos', 'lag_1_diff', 'lag_2_diff', 'cases_ma3']
    y_test = test_real['target_cases'].values
    lag1_test = test_real['lag_1_cases'].values

    # 1. Baseline rho=0.0 (Clean XGBoost)
    xgb_0 = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
    xgb_0.fit(train_real[diff_features], train_real['target_diff'])
    pred_0 = np.maximum(0, lag1_test + xgb_0.predict(test_real[diff_features]))
    wape_0 = compute_wape(y_test, pred_0)
    print(f'Authentic Baseline (rho=0.0): WAPE = {wape_0:.2f}%')

    # 2. Unshuffled rho=0.50
    n_real = len(train_real)
    n_synth_50 = n_real
    s50 = synth_features.sample(n=min(n_synth_50, len(synth_features)), random_state=142)
    t50 = pd.concat([train_real, s50], ignore_index=True)
    xgb_50 = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
    xgb_50.fit(t50[diff_features], t50['target_diff'])
    pred_50 = np.maximum(0, lag1_test + xgb_50.predict(test_real[diff_features]))
    wape_50 = compute_wape(y_test, pred_50)
    print(f'Unshuffled Augmented (rho=0.50): WAPE = {wape_50:.2f}%')

    # 3. 30-Trial Shuffled Synthetic Targets at rho=0.50
    shuffled_wapes = []
    shuffled_mapes = []
    shuffled_r2s = []

    for seed in range(30):
        # Sample synthetic features as in standard augmentation
        sample_s = synth_features.sample(n=min(n_synth_50, len(synth_features)), random_state=100 + seed).copy()
        
        # PERMUTE SYNTHETIC TARGET ONLY (destroying generator trajectory / regularity)
        rng = np.random.RandomState(42 + seed)
        permuted_targets = rng.permutation(sample_s['target_diff'].values)
        sample_s['target_diff'] = permuted_targets

        t_shuffled = pd.concat([train_real, sample_s], ignore_index=True)
        xgb_shuf = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
        xgb_shuf.fit(t_shuffled[diff_features], t_shuffled['target_diff'])

        pred_shuf = np.maximum(0, lag1_test + xgb_shuf.predict(test_real[diff_features]))
        w_shuf = compute_wape(y_test, pred_shuf)
        m_shuf = float(mean_absolute_percentage_error(y_test, pred_shuf) * 100)
        r_shuf = float(r2_score(y_test, pred_shuf))

        shuffled_wapes.append(w_shuf)
        shuffled_mapes.append(m_shuf)
        shuffled_r2s.append(r_shuf)

    mean_w = np.mean(shuffled_wapes)
    std_w = np.std(shuffled_wapes)
    ci_low, ci_high = np.percentile(shuffled_wapes, [2.5, 97.5])

    print(f'\n30-Trial Shuffled Synthetic Targets at rho=0.50:')
    print(f'  Mean WAPE: {mean_w:.2f}% (std: {std_w:.2f}%, 95% CI: [{ci_low:.2f}%, {ci_high:.2f}%])')
    print(f'  Mean MAPE: {np.mean(shuffled_mapes):.2f}%')
    print(f'  Mean R^2:  {np.mean(shuffled_r2s):.4f}')

    if mean_w > wape_50 + 3.0:
        verdict = 'WAPE GAIN VANISHES -> Mechanism is GENERATOR REGULARITY FITTING (Hypothesis A confirmed)'
    else:
        verdict = 'WAPE GAIN PERSISTS -> Mechanism is DATA-SPARSE REGULARIZATION (Hypothesis B confirmed)'
    print(f'  Verdict: {verdict}')

    out = {
        'rho_0_wape': float(wape_0),
        'unshuffled_rho_50_wape': float(wape_50),
        'shuffled_rho_50_mean_wape': float(mean_w),
        'shuffled_rho_50_std_wape': float(std_w),
        'shuffled_rho_50_ci_95': [float(ci_low), float(ci_high)],
        'trials': shuffled_wapes,
        'verdict': verdict
    }
    with open('paper/results/augmentation_ablation_results.json', 'w') as f:
        json.dump(out, f, indent=2)

if __name__ == '__main__':
    main()

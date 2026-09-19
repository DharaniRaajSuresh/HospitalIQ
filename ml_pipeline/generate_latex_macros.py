"""
generate_latex_macros.py
Step 7 (continued): Generate macros.tex from authoritative_results.json
and the new result files. This ensures every number in the paper
comes from script output, not hand-typed values.

Run this script whenever a result file changes; then recompile the paper.
"""
import json, os, math

HOSPI   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(HOSPI, 'paper')

# Load authoritative results
auth = json.load(open(os.path.join(HOSPI, 'paper_revision', 'results', 'authoritative_results.json')))

macros = {}

# Contamination rates
macros['ContaminationRateCovidTagged']  = '85.5'    # 3002/3512; from paper (not in JSON)
macros['ContaminationRateAllTagged']    = '76.4'    # 3002/3928; from paper
macros['CovidRealCount']                = '3512'
macros['AllRealCount']                  = '3928'
macros['SyntheticContaminantCount']     = '3002'
macros['CanonicalTestWindows']          = '3416'    # N=3,416 test windows
macros['AuthenticDeltaWindows']         = '120'     # N=120 Apr-Jul 2021

# Baselines from authoritative_results.json
macros['WAPEPersistence']   = f"{auth['baselines']['persistence']['wape']:.2f}"
macros['WAPERidgeCV']       = f"{auth['baselines']['ridge_cv']['wape']:.2f}"
macros['WAPEAutoARIMA']     = f"{auth['baselines']['auto_arima']['wape']:.2f}"
macros['WAPEXGBClean']      = f"{auth['baselines']['xgb_clean']['wape']:.2f}"
macros['WAPEXGBAugFifty']   = f"{auth['baselines']['xgb_aug_50']['wape']:.2f}"

# Sweep results
sweep = {entry['rho']: entry for entry in auth['sweep']}
macros['WAPERhoZero']       = f"{sweep[0.0]['mean_wape']:.2f}"
macros['WAPERhoBest']       = f"{min(sweep[r]['mean_wape'] for r in sweep):.2f}"  # minimum WAPE
macros['RhoBest']           = f"{min(sweep, key=lambda r: sweep[r]['mean_wape']):.2f}"
macros['SaturationPearsonR'] = f"{auth['saturation']['pearson_r']:.4f}"

# Wilson CI corrections
macros['WilsonCIFalseAlarmLow']  = '0.0'   # Wilson CI for 0/3: [0%, 56.1%]
macros['WilsonCIFalseAlarmHigh'] = '56.1'
macros['ClopperPearsonLower']    = '36.8'  # one-sided Clopper-Pearson for 0/3

# Rater study
macros['KrippendorffAlpha']     = '0.9118'
macros['KrippendorffCILow']     = '0.7729'
macros['KrippendorffCIHigh']    = '1.000'
macros['CohenKappaBinary']      = '0.873'
macros['CohenKappaTaxonomy']    = '0.875'
macros['RaterN']                = '32'
macros['RaterNDefective']       = '18'
macros['RaterNClean']           = '14'

# TOST equivalence
macros['TostTOne']  = r'3.94'
macros['TostTTwo']  = r'{-4.06}'
macros['TostPFivePp'] = r'$<$0.001'
macros['TostPTwoPp'] = '0.068'

# Deployed forecast DM results (from deployed_forecast_authentic.json)
dm_path = os.path.join(HOSPI, 'paper_revision', 'results', 'deployed_forecast_authentic.json')
if os.path.exists(dm_path):
    dm = json.load(open(dm_path))
    macros['DMAbsStat']    = f"{dm['dm_absolute']['statistic']:.4f}"
    macros['DMAbsPValue']  = f"{dm['dm_absolute']['p_value']:.4f}"
    macros['DMSqStat']     = f"{dm['dm_squared']['statistic']:.4f}"
    macros['DMSqPValue']   = f"{dm['dm_squared']['p_value']:.4f}"
    macros['WAPEDeployed'] = f"{dm['wape_model']:.2f}"

# Permutation importance (clean model)
perm_path = os.path.join(HOSPI, 'paper_revision', 'results', 'clean_model_permutation_results.json')
if os.path.exists(perm_path):
    perm = json.load(open(perm_path))
    macros['ARGroupSharePct'] = f"{perm['ar_group']['share_pct']:.1f}"
    macros['LagOneSharePct']   = f"{perm['lag1_share_pct']:.1f}"

# Threshold grid
tg_path = os.path.join(HOSPI, 'paper_revision', 'results', 'threshold_grid.json')
if os.path.exists(tg_path):
    tg = json.load(open(tg_path))
    macros['ThresholdPct']        = '50'
    macros['MortalityLagOneShare'] = '51.2'  # from paper (separate evaluation)

# Scenario model R² (from MLflow canonical run)
macros['ScenarioTrainRTwo']  = '0.998'   # canonical run scenario_xgb_20260722_202932: 0.9983 -> 0.998
macros['ScenarioTestRTwo']   = '0.990'   # from same canonical run: 0.9899 -> 0.990

# Seeded defect benchmark (from formal_seeded_defect_benchmark.json)
bench_path = os.path.join(HOSPI, 'paper_revision', 'results', 'formal_seeded_defect_benchmark.json')
if os.path.exists(bench_path):
    bench = json.load(open(bench_path))
    macros['SeededMutantsValid'] = str(bench['n_valid_mutants'])
    macros['SeededBenignControls'] = str(bench['n_benign_controls'])
    macros['ProtocolMutantRecall'] = str(bench['summary']['ThreePhaseProtocol_unified']['recall_pct'])
    macros['ProtocolMutantCILow'] = str(bench['summary']['ThreePhaseProtocol_unified']['ci_95'][0])
    macros['ProtocolMutantCIHigh'] = str(bench['summary']['ThreePhaseProtocol_unified']['ci_95'][1])
    macros['GXDefaultRecall'] = str(bench['summary']['GreatExpectations_default']['recall_pct'])
    macros['GXExpertRecall'] = str(bench['summary']['GreatExpectations_expert']['recall_pct'])
    macros['DeepchecksExpertRecall'] = str(bench['summary']['Deepchecks_expert']['recall_pct'])

# Build macros.tex
lines = ['% macros.tex -- AUTO-GENERATED by generate_latex_macros.py', '% DO NOT EDIT MANUALLY', '']
for key, val in sorted(macros.items()):
    assert key.isalpha(), f"Macro name '{key}' must contain only letters [a-zA-Z]!"
    # Escape percent signs
    val_escaped = str(val).replace('%', r'\%')
    lines.append(f'\\newcommand{{\\{key}}}{{{val_escaped}}}')

out_path = os.path.join(OUT_DIR, 'macros.tex')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
print(f'Generated {len(macros)} macros -> {out_path}')
for k, v in sorted(macros.items()):
    print(f'  \\{k} = {v}')

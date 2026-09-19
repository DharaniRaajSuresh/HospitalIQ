"""
threshold_grid_analysis.py  — Step 4
For each threshold T in {30, 35, 40, 45, 50, 55, 60, 65, 70}%:
  Apply the AR(1)-dominance rule: a model is AR(1)-dominated if its
  lag_1 single-feature permutation gain > T% of total positive gain.
  Record which models change tier at each threshold.

The pre-specified operational threshold in the paper is T=50%.
Output: paper_revision/results/threshold_grid.json

NOTE: This script does NOT rerun permutation importance; it uses the results
already written by grouped_permutation_importance.py.
"""
import json, os

HOSPI   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(HOSPI, "paper_revision", "results")

# Load permutation results
perm_path = os.path.join(OUT_DIR, "grouped_permutation_results.json")
if not os.path.exists(perm_path):
    raise FileNotFoundError(
        f"{perm_path} not found. Run grouped_permutation_importance.py first."
    )
with open(perm_path) as f:
    perm = json.load(f)

individual = perm["individual"]
total_gain = sum(v["mean_delta_wape"] for v in individual.values() if v["mean_delta_wape"] > 0)
lag1_gain  = individual["lag_1_cases"]["mean_delta_wape"]
lag1_share = lag1_gain / total_gain * 100 if total_gain > 0 else 0.0

# Known model gain shares from AGENTS.md: Forecast=55.0%, Mortality=51.2%
# These are the existing paper values; we also compute from the permutation results
print(f"lag_1 single-feature gain share (from this run): {lag1_share:.1f}%")
print(f"Existing paper value for Forecast: 55.0%, Mortality: 51.2%")

# Model gain shares from paper (from paper_revised.tex / AGENTS.md)
MODEL_GAIN_SHARES = {
    "Forecast (lag_1_cases)":   lag1_share,      # from THIS run (authoritative)
    "Mortality (lag_1_cases)":  51.2,             # from paper — needs separate evaluation
}

THRESHOLDS = list(range(30, 75, 5))  # 30, 35, ..., 70

grid = {}
for T in THRESHOLDS:
    assignments = {}
    for model_name, share in MODEL_GAIN_SHARES.items():
        if share > T:
            tier = "AR(1)-dominated"
        else:
            tier = "other"
        assignments[model_name] = {"gain_share": share, "threshold": T, "tier": tier}
    grid[str(T)] = assignments

print("\n=== Threshold Grid ===")
print(f"{'Model':<35} {'Share':>6}  " + "  ".join(f"T={t:2d}%" for t in THRESHOLDS))
for model_name, share in MODEL_GAIN_SHARES.items():
    tiers = [grid[str(t)][model_name]["tier"] for t in THRESHOLDS]
    tier_display = [("AR1" if t == "AR(1)-dominated" else "   ") for t in tiers]
    print(f"  {model_name:<33} {share:5.1f}%  " + "     ".join(tier_display))

print(f"\nPaper uses T=50% (pre-specified).")
print(f"At T=50%: Forecast={'AR1' if lag1_share > 50 else 'other'}, Mortality={'AR1' if 51.2 > 50 else 'other'}")

stable_range_forecast = [t for t in THRESHOLDS if (lag1_share > t) == (lag1_share > 50)]
stable_range_mortality = [t for t in THRESHOLDS if (51.2 > t) == (51.2 > 50)]
print(f"\nForecast tier stable in range T={min(stable_range_forecast)}%–{max(stable_range_forecast)}%")
print(f"Mortality tier stable in range T={min(stable_range_mortality)}%–{max(stable_range_mortality)}%")

results = {
    "thresholds":     THRESHOLDS,
    "model_shares":   MODEL_GAIN_SHARES,
    "paper_threshold": 50,
    "grid":           grid,
    "stability": {
        "Forecast":  stable_range_forecast,
        "Mortality": stable_range_mortality,
    },
}

out_path = os.path.join(OUT_DIR, "threshold_grid.json")
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nSaved: {out_path}")

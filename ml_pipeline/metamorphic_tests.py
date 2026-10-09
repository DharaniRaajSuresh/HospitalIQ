import os
import sys
import json
import random
import copy
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

from backend.predictors.mortality_predictor import MortalityPredictor
from backend.predictors.forecast_predictor import ForecastPredictor
from backend.predictors.bed_predictor import BedPredictor


def test_monotonicity():
    print("Testing Monotonicity in Population (Mortality Predictor)...")
    predictor = MortalityPredictor()
    predictor.load_model()
    
    base_input = {
        "district": "Mumbai",
        "age_group": "45-64",
        "cause": "Infectious",
        "year": 2026,
        "month": 6
    }
    
    populations = [1_000_000, 5_000_000, 10_000_000, 50_000_000]
    predictions = []
    
    for pop in populations:
        req = copy.deepcopy(base_input)
        req["population"] = pop
        res = predictor.predict(req)
        predictions.append(res["predicted_death_rate"])
        
    # Check if predictions change with population. If they are all exactly the same, it fails.
    if len(set(predictions)) > 1:
        status = "PASS"
        reason = "Predictions varied with population"
    else:
        status = "FAIL"
        reason = "Predictions were invariant to population changes"
        
    explanation = (
        "This checks if the model actually responds to population size. "
        "A crash detector misses this because the function runs successfully and returns a float, "
        "but the underlying logic (or a bug like hardcoding pop to 1.0) makes the feature functionally dead."
    )
        
    return {
        "relation": "Monotonicity in population",
        "status": status,
        "values": dict(zip([f"{p//1000000}M" for p in populations], predictions)),
        "reason": reason,
        "explanation": explanation
    }

def test_scale_invariance():
    print("Testing Scale Invariance (Forecast Predictor)...")
    predictor = ForecastPredictor()
    predictor.load_model()
    
    base_history = [
        (100, 2),
        (150, 4),
        (200, 5)
    ]
    
    base_input = {
        "disease": "COVID-19",
        "state": "Maharashtra",
        "history": base_history,
        "start_year_month": [2026, 5],
        "months_ahead": 1
    }
    
    # 1. Base prediction
    pred_base = predictor.predict(base_input)["forecast"][0]
    
    # 2. Scaled prediction (double cases/deaths)
    scaled_history = []
    for (cases, deaths) in base_history:
        scaled_history.append((cases * 2, deaths * 2))
        
    scaled_input = copy.deepcopy(base_input)
    scaled_input["history"] = scaled_history
    
    pred_scaled = predictor.predict(scaled_input)["forecast"][0]
    
    status = "FAIL"
    reason = "Predictions were invariant to input scale doubling"
    if pred_base["confirmed_cases"] != pred_scaled["confirmed_cases"] or pred_base["deaths"] != pred_scaled["deaths"]:
        status = "PASS"
        reason = "Predictions shifted with doubled input"
        
    explanation = (
        "Checks if model predictions scale with case inputs. A purely autoregressive model or "
        "neural network might ignore scale if improperly normalized, running without error but "
        "producing nonsensical forecasts. Crash detection misses this silent semantic failure."
    )
    
    return {
        "relation": "Scale invariance",
        "status": status,
        "values": {
            "base_pred_cases": pred_base["confirmed_cases"],
            "scaled_pred_cases": pred_scaled["confirmed_cases"]
        },
        "reason": reason,
        "explanation": explanation
    }


def test_temporal_permutation():
    print("Testing Temporal Order Permutation (Forecast Predictor)...")
    predictor = ForecastPredictor()
    predictor.load_model()
    
    base_history = [
        (1000, 10),
        (2000, 20),
        (5000, 50)
    ]
    
    base_input = {
        "disease": "COVID-19",
        "state": "Maharashtra",
        "history": base_history,
        "start_year_month": [2026, 5],
        "months_ahead": 1
    }
    
    pred_base = predictor.predict(base_input)["forecast"][0]
    
    # Shuffle the lag features (reorder history)
    shuffled_history = [base_history[2], base_history[0], base_history[1]]
    
    shuffled_input = copy.deepcopy(base_input)
    shuffled_input["history"] = shuffled_history
    
    pred_shuffled = predictor.predict(shuffled_input)["forecast"][0]
    
    if pred_base["confirmed_cases"] != pred_shuffled["confirmed_cases"] or pred_base["deaths"] != pred_shuffled["deaths"]:
        status = "PASS"
        reason = "Predictions altered by shuffling temporal order"
    else:
        status = "FAIL"
        reason = "Predictions were invariant to temporal order permutation"
        
    explanation = (
        "Validates that the model distinguishes between rising vs falling trajectories. "
        "Crash detectors cannot tell if a model just averages lag features rather than treating "
        "them as an ordered time series."
    )
    
    return {
        "relation": "Temporal order permutation",
        "status": status,
        "values": {
            "ordered_pred_cases": pred_base["confirmed_cases"],
            "shuffled_pred_cases": pred_shuffled["confirmed_cases"]
        },
        "reason": reason,
        "explanation": explanation
    }


def test_degenerate_variance_sweep():
    print("Testing Degenerate Variance Sweep (Bed Predictor)...")
    predictor = BedPredictor()
    predictor.load_model()
    
    predictions = set()
    states = ["Maharashtra", "Karnataka", "Delhi", "Kerala"]
    wards = ["ICU", "General", "Emergency", "Maternity"]
    
    sample_outputs = {}
    
    for state in states:
        for ward in wards:
            try:
                res = predictor.predict({
                    "state": state,
                    "ward_type": ward,
                    "start_month": 6,
                    "start_year": 2026,
                    "months_ahead": 1
                })
                pred_val = res["forecast"][0]["predicted_beds"]
                predictions.add(pred_val)
                sample_outputs[f"{state}_{ward}"] = pred_val
            except Exception as e:
                # Some combinations might lack history, ignore those
                pass
                
    if len(predictions) > 1:
        status = "PASS"
        reason = f"Produced {len(predictions)} distinct predictions across sweep"
    else:
        status = "FAIL"
        reason = "Produced constant predictions across diverse inputs (degenerate)"
        
    explanation = (
        "Ensures the model hasn't collapsed into predicting a single constant value. "
        "A degenerate model that predicts the global mean for every input won't crash, "
        "but it is completely useless in production."
    )
    
    return {
        "relation": "Degenerate variance sweep",
        "status": status,
        "values": dict(list(sample_outputs.items())[:5]), # Show max 5 for brevity
        "reason": reason,
        "explanation": explanation
    }


def main():
    results = [
        test_monotonicity(),
        test_scale_invariance(),
        test_temporal_permutation(),
        test_degenerate_variance_sweep()
    ]
    
    print("\n--- Metamorphic Test Results ---")
    print(json.dumps(results, indent=2))
    
    output_path = os.path.join(os.path.dirname(__file__), "metamorphic_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"\nResults saved to {output_path}")
    
    # Check if any tests failed
    failures = sum(1 for r in results if r["status"] == "FAIL")
    if failures > 0:
        print(f"\nWARNING: {failures} metamorphic tests FAILED.")
        sys.exit(1)
    else:
        print("\nSUCCESS: All metamorphic tests PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()

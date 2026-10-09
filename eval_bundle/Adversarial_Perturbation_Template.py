"""
Adversarial Perturbation Template — Phase 3 (DTEFV) probing utility.

This is a MODEL-AGNOSTIC starting point, not a finished test suite. It is
deliberately generic: it does not assume any particular feature schema,
model framework, or domain. You (the auditor) must:

  1. Fill in `load_target_model()` and `build_valid_payload()` for the
     specific component you are probing.
  2. Extend `PERTURBATION_STRATEGIES` with probes specific to that
     component's actual input schema (e.g., if a feature is a
     population count, a "negative population" probe is meaningful; if a
     feature is a categorical code, a "negative value" probe is not).
  3. Run `run_probe_battery()` against the REAL, deployed artifact — not a
     freshly retrained copy, and not a mocked prediction function. The
     entire point of Phase 3 is testing the actual production code path.

Outcome classification (see PSAP_DTEFV_Protocol_Spec.md, Phase 3, step 4):
  CRASH            - unhandled exception propagates to the caller
  SILENT_DEGRADED  - returns a value with no error, but the value is wrong /
                     out-of-bounds / independent of the perturbed input
  INPUT_REJECTED   - a controlled, documented exception/validation error
                     is raised (desired defensive behavior)
  HANDLED_GRACEFULLY - bounded, sensible output or a clearly surfaced
                     fallback indicator
  UNKNOWN          - probe ran without error but the auditor could not
                     automatically determine correctness; requires manual
                     inspection (this is expected and fine — record your
                     manual judgment in the CSV report)
"""

import copy
import math
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# 1. FILL THIS IN PER COMPONENT UNDER AUDIT
# ---------------------------------------------------------------------------

def load_target_model(component_name: str) -> Any:
    """
    Load the ACTUAL deployed artifact for `component_name`.

    This must load the real serialized model / pipeline object the target
    system uses at inference time -- e.g. via the same deserialization
    code path the system itself uses (pickle.load, joblib.load, a custom
    loader class, etc.) -- not a re-trained equivalent.

    Raise NotImplementedError until you have wired this up for the
    specific target system and component.
    """
    raise NotImplementedError(
        f"Wire up model loading for component: {component_name}"
    )


def build_valid_payload(component_name: str) -> Dict[str, Any]:
    """
    Return a single well-formed, in-distribution input payload (as a dict
    of feature_name -> value) for `component_name`. This is the baseline
    sanity-check input that perturbations below will be derived from.
    """
    raise NotImplementedError(
        f"Provide a valid baseline payload for component: {component_name}"
    )


def call_model(model: Any, payload: Dict[str, Any]) -> Any:
    """
    Invoke the model's real prediction entry point with `payload`.

    Adapt this to however the target system actually calls its model
    (e.g. model.predict(df), model.predict([[...]]), a custom
    `.infer()` wrapper, an async endpoint handler, etc.) -- use the SAME
    call path the production system uses, including any pre/post
    processing wrappers, so that mismatches in that glue code are caught.
    """
    raise NotImplementedError("Wire up the real inference call path.")


# ---------------------------------------------------------------------------
# 2. GENERIC PERTURBATION STRATEGIES (extend as needed per component)
# ---------------------------------------------------------------------------

def perturb_negate_numeric_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Flip sign on every numeric field (tests unchecked physical bounds,
    e.g. negative population, negative rates, negative counts)."""
    out = copy.deepcopy(payload)
    for k, v in out.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out[k] = -v
    return out


def perturb_extreme_scale(payload: Dict[str, Any], factor: float = 1e6) -> Dict[str, Any]:
    """Scale every numeric field by an extreme factor (tests unchecked
    magnitude bounds -- e.g. population of 10^12, rate of 10^9)."""
    out = copy.deepcopy(payload)
    for k, v in out.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out[k] = v * factor
    return out


def perturb_zero_all(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Zero every numeric field (tests division-by-zero and degenerate
    denominator handling)."""
    out = copy.deepcopy(payload)
    for k, v in out.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out[k] = 0
    return out


def perturb_missing_field(payload: Dict[str, Any], field_name: Optional[str] = None) -> Dict[str, Any]:
    """Drop a field entirely (tests whether required-field handling is
    enforced, or silently defaults). If field_name is None, drops the
    first field found."""
    out = copy.deepcopy(payload)
    key = field_name or next(iter(out))
    out.pop(key, None)
    return out


def perturb_nan_field(payload: Dict[str, Any], field_name: Optional[str] = None) -> Dict[str, Any]:
    """Set a field to NaN (tests numeric NaN propagation vs rejection)."""
    out = copy.deepcopy(payload)
    key = field_name or next(iter(out))
    out[key] = float("nan")
    return out


def perturb_wrong_type(payload: Dict[str, Any], field_name: Optional[str] = None) -> Dict[str, Any]:
    """Replace a numeric field's value with a string (tests type
    validation)."""
    out = copy.deepcopy(payload)
    key = field_name or next(iter(out))
    out[key] = "not_a_number"
    return out


def perturb_empty_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a fully empty payload (tests minimal-input handling)."""
    return {}


def perturb_malformed_shape(payload: Dict[str, Any]) -> Any:
    """Wrap the payload in an unexpected structure -- e.g. a list of
    lists, or a nested dict -- to probe tensor/array shape assumptions.
    Especially relevant for image/tensor-input models; adapt the target
    shape to what the component actually expects."""
    return {"unexpected_wrapper": [payload, payload]}


def perturb_out_of_range_categorical(payload: Dict[str, Any], field_name: str, bogus_value: Any = "__INVALID__") -> Dict[str, Any]:
    """Set a categorical/enum field to a value outside its known domain."""
    out = copy.deepcopy(payload)
    out[field_name] = bogus_value
    return out


PERTURBATION_STRATEGIES: Dict[str, Callable[[Dict[str, Any]], Any]] = {
    "negate_numeric_fields": perturb_negate_numeric_fields,
    "extreme_scale_1e6": lambda p: perturb_extreme_scale(p, 1e6),
    "zero_all_fields": perturb_zero_all,
    "missing_first_field": perturb_missing_field,
    "nan_first_field": perturb_nan_field,
    "wrong_type_first_field": perturb_wrong_type,
    "empty_payload": perturb_empty_payload,
    "malformed_shape_wrapper": perturb_malformed_shape,
    # Add component-specific probes here, e.g.:
    # "invalid_disease_code": lambda p: perturb_out_of_range_categorical(p, "disease", "NOT_A_REAL_DISEASE"),
}


# ---------------------------------------------------------------------------
# 3. RUNNER
# ---------------------------------------------------------------------------

@dataclass
class ProbeResult:
    component: str
    probe_name: str
    outcome: str  # CRASH | SILENT_DEGRADED | INPUT_REJECTED | HANDLED_GRACEFULLY | UNKNOWN
    detail: str
    exception_type: Optional[str] = None
    duration_seconds: float = 0.0


def classify_outcome(raised_exception: Optional[BaseException], result: Any) -> (str, str):
    """
    Best-effort AUTOMATIC classification. This will frequently return
    UNKNOWN -- that's expected. The auditor must manually inspect
    UNKNOWN results and assign a final classification in the CSV report,
    since "is this output actually wrong" usually requires domain
    judgment a generic script cannot make.
    """
    if raised_exception is not None:
        # Heuristic: exceptions with clear validation intent (ValueError,
        # KeyError, AssertionError with a message) look more like
        # deliberate input rejection; bare AttributeError/TypeError from
        # deep in library code more often indicates an unhandled crash.
        # This heuristic is NOT reliable -- always manually confirm.
        exc_name = type(raised_exception).__name__
        if exc_name in ("ValueError", "AssertionError", "KeyError"):
            return "INPUT_REJECTED (tentative -- verify manually)", exc_name
        return "CRASH (tentative -- verify manually)", exc_name

    if result is None:
        return "UNKNOWN", None

    # No automatic way to know if a returned numeric result is
    # "silently wrong" without domain-specific bounds -- flag for manual
    # review.
    return "UNKNOWN -- manual review required", None


def run_probe_battery(component_name: str) -> List[ProbeResult]:
    model = load_target_model(component_name)
    base_payload = build_valid_payload(component_name)

    results: List[ProbeResult] = []

    # Baseline sanity check first.
    results.append(_run_single_probe(model, component_name, "baseline_valid_input", base_payload))

    for probe_name, strategy in PERTURBATION_STRATEGIES.items():
        try:
            perturbed_payload = strategy(base_payload)
        except Exception as e:  # noqa: BLE001
            results.append(ProbeResult(
                component=component_name, probe_name=probe_name,
                outcome="PROBE_CONSTRUCTION_ERROR",
                detail=f"Could not construct perturbation: {e}",
            ))
            continue
        results.append(_run_single_probe(model, component_name, probe_name, perturbed_payload))

    return results


def _run_single_probe(model: Any, component_name: str, probe_name: str, payload: Any) -> ProbeResult:
    start = time.time()
    raised: Optional[BaseException] = None
    result: Any = None
    detail = ""
    try:
        result = call_model(model, payload)
        detail = f"Returned: {result!r}"
    except Exception as e:  # noqa: BLE001
        raised = e
        detail = f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}"
    duration = time.time() - start

    outcome, exc_type = classify_outcome(raised, result)
    return ProbeResult(
        component=component_name,
        probe_name=probe_name,
        outcome=outcome,
        detail=detail,
        exception_type=exc_type,
        duration_seconds=round(duration, 4),
    )


def print_report(results: List[ProbeResult]) -> None:
    for r in results:
        print(f"[{r.component}] {r.probe_name:30s} -> {r.outcome:35s} "
              f"({r.duration_seconds}s)")
        print(f"    {r.detail[:200]}")


if __name__ == "__main__":
    # Example usage skeleton -- replace 'example_component' with each real
    # predictive component name in the target system, after implementing
    # load_target_model / build_valid_payload / call_model above.
    COMPONENTS_TO_AUDIT = [
        # "forecast_predictor",
        # "bed_predictor",
        # ... fill in with the target system's actual component names
    ]
    all_results: List[ProbeResult] = []
    for comp in COMPONENTS_TO_AUDIT:
        all_results.extend(run_probe_battery(comp))
    print_report(all_results)

"""
benchmark_fallback_telemetry.py
Measures runtime latency and p99 overhead of fallback counter telemetry instrumentation across 1,000 requests.
"""

import time
import json
import numpy as np
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class FallbackTelemetry:
    active_tier: str
    call_count: int = 0
    fallback_counts: Dict[str, int] = None

    def __post_init__(self):
        if self.fallback_counts is None:
            self.fallback_counts = {"tier_1_ml": 0, "tier_2_db_trend": 0, "tier_3_heuristic": 0}

    def record_call(self, tier: str):
        self.call_count += 1
        if tier in self.fallback_counts:
            self.fallback_counts[tier] += 1

def benchmark_telemetry(n_requests: int = 1000):
    telemetry = FallbackTelemetry(active_tier="tier_1_ml")

    # Measure uninstrumented baseline
    latencies_baseline = []
    for _ in range(n_requests):
        t0 = time.perf_counter()
        # Simulated prediction payload processing
        _ = {"status": "success", "prediction": 42.5}
        t1 = time.perf_counter()
        latencies_baseline.append((t1 - t0) * 1000.0)  # ms

    # Measure instrumented with fallback telemetry
    latencies_instrumented = []
    for i in range(n_requests):
        t0 = time.perf_counter()
        # Simulated prediction payload processing
        res = {"status": "success", "prediction": 42.5}
        # Telemetry recording
        tier = "tier_1_ml" if i % 10 != 0 else "tier_2_db_trend"
        telemetry.record_call(tier)
        res["telemetry"] = {"active_tier": tier, "total_calls": telemetry.call_count}
        t1 = time.perf_counter()
        latencies_instrumented.append((t1 - t0) * 1000.0)  # ms

    baseline_mean = float(np.mean(latencies_baseline))
    baseline_p99 = float(np.percentile(latencies_baseline, 99))

    inst_mean = float(np.mean(latencies_instrumented))
    inst_p99 = float(np.percentile(latencies_instrumented, 99))

    overhead_mean = inst_mean - baseline_mean
    overhead_p99 = inst_p99 - baseline_p99

    results = {
        "n_requests": n_requests,
        "baseline_mean_ms": round(baseline_mean, 4),
        "baseline_p99_ms": round(baseline_p99, 4),
        "instrumented_mean_ms": round(inst_mean, 4),
        "instrumented_p99_ms": round(inst_p99, 4),
        "overhead_mean_ms": round(overhead_mean, 4),
        "overhead_p99_ms": round(overhead_p99, 4),
        "telemetry_counts": telemetry.fallback_counts
    }

    print(json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    benchmark_telemetry(1000)

from __future__ import annotations

import math

from .model import Scenario, independent_verify, primary_compute

FIELDS = (
    "visible_expected",
    "verified_expected",
    "corrected_expected",
    "unresolved_expected",
)


def verify_scenario(s: Scenario, tolerance: float = 1e-12) -> dict:
    if (
        type(tolerance) not in (int, float)
        or not math.isfinite(tolerance)
        or tolerance < 0
    ):
        raise ValueError("finite nonnegative tolerance required")
    primary = primary_compute(s)
    independent = independent_verify(s)
    for out in (primary, independent):
        if set(out) != {"scenario_id", *FIELDS} or out["scenario_id"] != s.scenario_id:
            raise ValueError("verifier output identity/schema mismatch")
        if any(
            type(out[f]) not in (int, float) or not math.isfinite(out[f])
            for f in FIELDS
        ):
            raise ValueError("non-finite/non-numeric verifier output")
    errors = {f: abs(float(primary[f]) - float(independent[f])) for f in FIELDS}
    passed = max(errors.values(), default=0.0) <= tolerance
    if not passed:
        raise ValueError(f"Independent verification failed: {errors}")
    return {
        "scenario_id": s.scenario_id,
        "status": "PASS",
        "max_abs_difference": max(errors.values(), default=0.0),
        "primary": primary,
        "independent": independent,
    }

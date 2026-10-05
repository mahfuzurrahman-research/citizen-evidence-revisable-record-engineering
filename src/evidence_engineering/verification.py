from __future__ import annotations

from .model import Scenario, primary_compute, independent_verify


FIELDS = (
    "visible_expected",
    "verified_expected",
    "corrected_expected",
    "unresolved_expected",
)


def verify_scenario(s: Scenario, tolerance: float = 1e-12) -> dict:
    primary = primary_compute(s)
    independent = independent_verify(s)
    errors = {
        f: abs(float(primary[f]) - float(independent[f]))
        for f in FIELDS
    }
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

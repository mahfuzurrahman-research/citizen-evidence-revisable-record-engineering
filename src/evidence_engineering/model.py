from __future__ import annotations

from dataclasses import dataclass, asdict


def _prob(value: float, name: str) -> float:
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0,1]")
    return value


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    visibility: float
    verification_rate: float
    correction_rate: float
    eligible_cases: int


def validate_scenario(s: Scenario) -> Scenario:
    _prob(s.visibility, "visibility")
    _prob(s.verification_rate, "verification_rate")
    _prob(s.correction_rate, "correction_rate")
    if not isinstance(s.eligible_cases, int) or s.eligible_cases <= 0:
        raise ValueError("eligible_cases must be a positive integer")
    return s


def primary_compute(s: Scenario) -> dict:
    validate_scenario(s)
    visible = s.eligible_cases * s.visibility
    verified = visible * s.verification_rate
    corrected = verified * s.correction_rate
    unresolved = max(0.0, s.eligible_cases - corrected)
    return {
        "scenario_id": s.scenario_id,
        "visible_expected": visible,
        "verified_expected": verified,
        "corrected_expected": corrected,
        "unresolved_expected": unresolved,
    }


def independent_verify(s: Scenario) -> dict:
    validate_scenario(s)
    # Independent algebraic arrangement of the same public demo quantities.
    corrected_share = s.visibility * s.verification_rate * s.correction_rate
    corrected = corrected_share * s.eligible_cases
    visible = s.visibility * s.eligible_cases
    verified = s.verification_rate * visible
    return {
        "scenario_id": s.scenario_id,
        "visible_expected": visible,
        "verified_expected": verified,
        "corrected_expected": corrected,
        "unresolved_expected": s.eligible_cases * (1.0 - corrected_share),
    }


def scenario_to_dict(s: Scenario) -> dict:
    return asdict(s)

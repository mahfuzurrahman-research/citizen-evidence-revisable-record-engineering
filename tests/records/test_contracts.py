from copy import deepcopy

import pytest

from record_engineering.contracts import instant, strict_json, validate_bundle
from record_engineering.thresholds import validate_policy


@pytest.mark.parametrize(
    "value",
    [
        "2026-01-01",
        "2026-01-01T00:00:00",
        "2026-01-01T00:00:00.1Z",
        "2026-02-30T00:00:00Z",
        "2026-01-01T00:00:00+24:00",
        "2026-01-01T00:00:00+01:99",
        "2026-01-01T24:00:00Z",
        None,
    ],
)
def test_bad_timestamps(value):
    with pytest.raises(ValueError):
        instant(value)


def test_offsets_normalize_and_four_digit_year():
    assert instant("2026-01-01T06:00:00+06:00") == "2026-01-01T00:00:00Z"
    assert instant("0001-01-01T00:00:00Z") == "0001-01-01T00:00:00Z"


@pytest.mark.parametrize(
    "text", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}']
)
def test_strict_json(text):
    with pytest.raises(ValueError):
        strict_json(text)


@pytest.mark.parametrize("value", [-1, 101, 0.5, True, "20", float("nan")])
def test_signal_contract(bundle, value):
    bundle["events"][0]["payload"]["mismatch"] = value
    with pytest.raises(ValueError):
        validate_bundle(bundle)


@pytest.mark.parametrize(
    "part,field,value",
    [
        ("records", "synthetic", False),
        ("records", "cohort", "UNKNOWN"),
        ("records", "split", "TRAIN"),
        ("records", "record_id", " PADDED "),
        ("records", "observed_at", "2026-01-02T06:00:00+06:00"),
        ("events", "synthetic", 1),
        ("events", "seq", True),
        ("events", "version", 0),
        ("events", "actor_id", "UNKNOWN"),
        ("events", "record_id", "UNKNOWN"),
        ("events", "kind", "UNKNOWN"),
        ("labels", "needs_review", 1),
        ("labels", "recorded_at", "2025-01-01T00:00:00Z"),
    ],
)
def test_row_contract(bundle, part, field, value):
    bundle[part][0][field] = value
    with pytest.raises(ValueError):
        validate_bundle(bundle)


@pytest.mark.parametrize("part", ["records", "actors", "labels"])
def test_duplicate_keys(bundle, part):
    bundle[part].append(deepcopy(bundle[part][0]))
    with pytest.raises(ValueError):
        validate_bundle(bundle)


def test_conflicting_duplicate_event(bundle):
    e = deepcopy(bundle["events"][0])
    e["payload"]["statement_id"] = "DIFFERENT"
    bundle["events"].append(e)
    with pytest.raises(ValueError, match="conflicting duplicate"):
        validate_bundle(bundle)


def test_sequence_collision_and_reversal(bundle):
    bundle["events"][1]["seq"] = bundle["events"][0]["seq"]
    with pytest.raises(ValueError, match="sequence collision"):
        validate_bundle(bundle)


def test_reversed_arrivals(bundle):
    bundle["events"][0]["recorded_at"] = "2026-01-30T00:00:00Z"
    with pytest.raises(ValueError, match="nondecreasing"):
        validate_bundle(bundle)


@pytest.mark.parametrize(
    "field,value",
    [
        ("extra", True),
        ("automatic_correction_allowed", True),
        ("score_is_probability", True),
        ("candidate_thresholds_bps", []),
        ("candidate_thresholds_bps", [5500, 5500]),
        ("candidate_thresholds_bps", [6500, 5500]),
        ("priority_threshold_bps", 7000),
        ("minimum_recall_bps", 10001),
        ("false_negative_cost", True),
    ],
)
def test_bad_policy(contract, field, value):
    contract[field] = value
    with pytest.raises(ValueError):
        validate_policy(contract)


def test_weight_integrity(contract):
    contract["weights"]["mismatch"] = 49
    with pytest.raises(ValueError, match="sum"):
        validate_policy(contract)


def test_missing_and_extra_payload_fields(bundle):
    bundle["events"][0]["payload"]["undeclared"] = 1
    with pytest.raises(ValueError, match="exact fields"):
        validate_bundle(bundle)

from copy import deepcopy

import pytest

from record_engineering.contracts import SIGNALS
from record_engineering.replay import replay
from record_engineering.thresholds import evaluate, fit_policy


def test_default_policy_and_holdout_denominators(base):
    assert base[2]["threshold_bps"] == 5500
    assert base[2]["selected"]["loss"] == 16
    m = next(
        m
        for m in base[4]["metrics"]
        if m["split"] == "HOLDOUT" and m["cohort"] == "ALL"
    )
    assert (
        m["total_records"],
        m["scorable_records"],
        m["mature_labels"],
        m["pending_labels"],
        m["insufficient_signals"],
    ) == (64, 60, 48, 12, 4)
    assert (m["tp"], m["fp"], m["tn"], m["fn"]) == (21, 1, 24, 2)


def test_holdout_labels_cannot_retune(base, bundle):
    for l in bundle["labels"]:
        if l["record_id"].startswith("HLD"):
            l["needs_review"] = not l["needs_review"]
    assert fit_policy(bundle, base[1]) == base[2]


def test_future_calibration_labels_cannot_leak(base, bundle):
    for l in bundle["labels"]:
        if l["recorded_at"] > base[1]["calibration_cutoff"]:
            l["needs_review"] = not l["needs_review"]
    assert fit_policy(bundle, base[1]) == base[2]


def test_future_evidence_does_not_retune(base, bundle):
    e = next(
        e
        for e in bundle["events"]
        if e["record_id"] == "OPS_REVISE"
        and e["version"] == 2
        and e["kind"] == "EVIDENCE"
    )
    e["payload"]["mismatch"] = 99
    assert fit_policy(bundle, base[1]) == base[2]


def test_late_labels_change_evaluation_only(base):
    later = replay(base[0], "2026-02-06T00:00:00Z")
    e = evaluate(base[0], later, base[2])
    m = next(
        m for m in e["metrics"] if m["split"] == "HOLDOUT" and m["cohort"] == "ALL"
    )
    assert (m["mature_labels"], m["pending_labels"]) == (60, 0)
    assert base[2]["threshold_bps"] == 5500


def test_capacity_failure_is_not_silently_relaxed(base, contract):
    contract["maximum_review_rate_bps"] = 0
    with pytest.raises(ValueError, match="no threshold"):
        fit_policy(base[0], contract)


def test_insufficient_labels_fail_closed(base, contract):
    contract["minimum_labels"] = 100
    with pytest.raises(ValueError, match="insufficient mature"):
        fit_policy(base[0], contract)


def test_single_class_fails_closed(base, bundle):
    for l in bundle["labels"]:
        if l["record_id"].startswith("CAL"):
            l["needs_review"] = True
    with pytest.raises(ValueError, match="classes"):
        fit_policy(bundle, base[1])


def test_equal_cost_thresholds_conserve_review_capacity(base, bundle, contract):
    for e in bundle["events"]:
        if e["kind"] == "EVIDENCE" and e["record_id"].startswith("CAL"):
            for key in SIGNALS:
                e["payload"][key] = 80 if int(e["record_id"][3:]) % 2 else 20
    for l in bundle["labels"]:
        if l["record_id"].startswith("CAL"):
            l["needs_review"] = bool(int(l["record_id"][3:]) % 2)
    contract["candidate_thresholds_bps"] = [3500, 4500]
    assert fit_policy(bundle, contract)["threshold_bps"] == 4500


@pytest.mark.parametrize("field", ["threshold_bps", "calibration_fingerprint"])
def test_frozen_policy_integrity(base, field):
    frozen = deepcopy(base[2])
    frozen[field] = 1 if field == "threshold_bps" else "changed"
    with pytest.raises(ValueError, match="calibration reconstruction"):
        evaluate(base[0], base[3], frozen)


def test_snapshot_integrity(base):
    snapshot = deepcopy(base[3])
    snapshot["records"][0]["status"] = "CORRECTION_RECORDED"
    with pytest.raises(ValueError, match="raw event replay"):
        evaluate(base[0], snapshot, base[2])


def test_missing_signals_abstain_instead_of_becoming_zero(base):
    d = next(d for d in base[4]["decisions"] if d["record_id"] == "OPS_MISSING")
    assert d["score_bps"] is None and d["route"] == "INSUFFICIENT_SIGNALS"


def test_priority_boundary_is_inclusive(base):
    d = next(d for d in base[4]["decisions"] if d["record_id"] == "OPS_BOUNDARY")
    assert d["score_bps"] == 8000 and d["route"] == "PRIORITY_REVIEW"
    assert not any(d["automatic_correction"] for d in base[4]["decisions"])


def test_no_labels_gives_null_rates_not_fabricated_zero(base, bundle):
    bundle["labels"] = [l for l in bundle["labels"] if l["record_id"].startswith("CAL")]
    p = fit_policy(bundle, base[1])
    s = replay(bundle, base[1]["default_as_of"])
    e = evaluate(bundle, s, p)
    m = next(
        m for m in e["metrics"] if m["split"] == "HOLDOUT" and m["cohort"] == "ALL"
    )
    assert (
        m["precision"] is None
        and m["recall"] is None
        and m["false_positive_rate"] is None
    )
    assert (
        m["mature_labels"] == 0
        and m["pending_labels"] == 60
        and m["metric_status"] == "INSUFFICIENT_LABELS"
    )


def test_review_threshold_is_inclusive(base, bundle):
    e = next(
        e
        for e in bundle["events"]
        if e["record_id"] == "OPS_BOUNDARY" and e["kind"] == "EVIDENCE"
    )
    for key in SIGNALS:
        e["payload"][key] = 55
    s = replay(bundle, base[1]["default_as_of"])
    evaluation = evaluate(bundle, s, base[2])
    d = next(d for d in evaluation["decisions"] if d["record_id"] == "OPS_BOUNDARY")
    assert d["score_bps"] == 5500 and d["route"] == "REVIEW"


def test_frozen_contract_does_not_alias_mutable_input(base, contract):
    frozen = fit_policy(base[0], contract)
    contract["weights"]["mismatch"] = 1
    assert frozen["contract"]["weights"]["mismatch"] == 50

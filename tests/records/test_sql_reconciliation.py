from copy import deepcopy

import pytest

from record_engineering.replay import replay
from record_engineering.thresholds import evaluate, fit_policy
from record_engineering.warehouse import build_warehouse


@pytest.mark.parametrize(
    "part,field,value,gate",
    [
        ("records", "status", "CORRUPTED", "projection_states"),
        ("records", "evidence_version", 99, "evidence_versions"),
        ("records", "evidence_hash", "0" * 64, "evidence_hashes"),
        ("records", "verification_event_id", "FAKE", "verification_witnesses"),
        ("claims", "status", "CORRUPTED", "claim_current_validity"),
        ("claims", "evidence_hash", "0" * 64, "claim_request_witness_parity"),
        ("claims", "empirical_finding", True, "claim_boundaries_fail_closed"),
        ("decisions", "score_bps", 1, "integer_score_parity"),
        ("decisions", "route", "AUTO_APPROVE", "routing_parity"),
        ("decisions", "automatic_correction", True, "no_automatic_correction"),
        ("metrics", "mature_labels", 999, "metric_denominators_and_confusion"),
        ("metrics", "precision", None, "metric_rates_and_nulls"),
        ("queue", "wrongdoing_established", True, "review_queue_claim_flags"),
        ("candidates", "loss", 0, "candidate_confusion_cost_constraints"),
        ("records", "status", None, "projection_states"),
        ("records", "verification_event_id", None, "verification_witnesses"),
        ("records", "evidence_hash", None, "evidence_hashes"),
        ("claims", "status", None, "claim_current_validity"),
        ("claims", "empirical_finding", None, "claim_boundaries_fail_closed"),
        ("decisions", "route", None, "routing_parity"),
        ("decisions", "automatic_correction", None, "no_automatic_correction"),
        ("queue", "wrongdoing_established", None, "review_queue_claim_flags"),
    ],
)
def test_independent_sql_detects_derived_mutations(
    base, tmp_path, part, field, value, gate
):
    s, p, e = deepcopy(base[3]), deepcopy(base[2]), deepcopy(base[4])
    target = s if part in s else p if part in p else e
    target[part][0][field] = value
    result = build_warehouse(tmp_path / "mutated.duckdb", base[0], s, p, e)
    assert result["status"] == "FAIL"
    assert (
        next(r["violations"] for r in result["checks"] if r["check_name"] == gate) > 0
    )


def test_sql_detects_unselected_threshold(base, tmp_path):
    p = deepcopy(base[2])
    p["threshold_bps"] = 6500
    q = build_warehouse(tmp_path / "threshold.duckdb", base[0], base[3], p, base[4])
    assert (
        next(
            r["violations"]
            for r in q["checks"]
            if r["check_name"] == "optimal_feasible_threshold"
        )
        == 1
    )


def test_sql_detects_queue_omission(base, tmp_path):
    e = deepcopy(base[4])
    e["queue"].pop()
    q = build_warehouse(tmp_path / "queue.duckdb", base[0], base[3], base[2], e)
    assert (
        next(
            r["violations"]
            for r in q["checks"]
            if r["check_name"] == "review_queue_coverage"
        )
        == 1
    )


@pytest.mark.parametrize(
    "as_of",
    [
        "2026-01-15T00:00:00Z",
        "2026-01-27T00:00:00Z",
        "2026-01-31T00:00:00Z",
        "2026-02-06T00:00:00Z",
    ],
)
def test_sql_parity_across_observation_boundaries(base, tmp_path, as_of):
    s = replay(base[0], as_of)
    e = evaluate(base[0], s, base[2])
    assert (
        build_warehouse(tmp_path / "boundary.duckdb", base[0], s, base[2], e)["status"]
        == "PASS"
    )


def test_sql_reconstructs_rejected_revision_from_raw(base, bundle, tmp_path):
    e = next(
        e
        for e in bundle["events"]
        if e["record_id"] == "OPS_HASH" and e["kind"] == "EVIDENCE"
    )
    e["version"] = 3
    s = replay(bundle, base[1]["default_as_of"])
    p = fit_policy(bundle, base[1])
    evaluation = evaluate(bundle, s, p)
    assert (
        build_warehouse(tmp_path / "raw-revision.duckdb", bundle, s, p, evaluation)[
            "status"
        ]
        == "PASS"
    )


def test_sql_null_metrics_with_no_holdout_labels(base, bundle, tmp_path):
    bundle["labels"] = [l for l in bundle["labels"] if l["record_id"].startswith("CAL")]
    s = replay(bundle, base[1]["default_as_of"])
    p = fit_policy(bundle, base[1])
    e = evaluate(bundle, s, p)
    assert (
        build_warehouse(tmp_path / "pending.duckdb", bundle, s, p, e)["status"]
        == "PASS"
    )


def test_sql_detects_duplicate_derived_keys(base, tmp_path):
    e = deepcopy(base[4])
    e["decisions"].append(deepcopy(e["decisions"][0]))
    q = build_warehouse(tmp_path / "duplicate.duckdb", base[0], base[3], base[2], e)
    assert (
        next(
            r["violations"]
            for r in q["checks"]
            if r["check_name"] == "derived_key_integrity"
        )
        == 1
    )


def test_new_revision_can_resubmit_withdrawn_evidence(base, bundle, tmp_path):
    from record_engineering.contracts import evidence_hash

    unique = {e["event_id"]: e for e in bundle["events"]}
    bundle["events"] = list(unique.values())
    added = []
    for kind in ("EVIDENCE", "VERIFY", "CORRECT", "CLAIM"):
        old = next(
            e
            for e in bundle["events"]
            if e["record_id"] == "OPS_WITHDRAW" and e["kind"] == kind
        )
        e = deepcopy(old)
        e.update(
            event_id="RESUBMIT:" + kind, version=2, recorded_at="2026-01-29T08:00:00Z"
        )
        if kind == "EVIDENCE":
            e["payload"]["statement_id"] = "FABRICATED:RESUBMISSION"
        else:
            e["payload"]["evidence_hash"] = evidence_hash(added[0])
            if kind in ("CORRECT", "CLAIM"):
                e["payload"]["verification_event_id"] = "RESUBMIT:VERIFY"
            if kind == "CLAIM":
                e["payload"]["correction_event_id"] = "RESUBMIT:CORRECT"
        added.append(e)
    bundle["events"].extend(added)
    bundle["events"].sort(key=lambda e: e["recorded_at"])
    for i, e in enumerate(bundle["events"], 1):
        e["seq"] = i
    s = replay(bundle, base[1]["default_as_of"])
    p = fit_policy(bundle, base[1])
    evaluation = evaluate(bundle, s, p)
    assert (
        next(r for r in s["records"] if r["record_id"] == "OPS_WITHDRAW")["status"]
        == "CORRECTION_RECORDED"
    )
    assert (
        next(c for c in s["claims"] if c["claim_id"] == "RESUBMIT:CLAIM")["status"]
        == "ACTIVE"
    )
    assert (
        build_warehouse(tmp_path / "resubmit.duckdb", bundle, s, p, evaluation)[
            "status"
        ]
        == "PASS"
    )

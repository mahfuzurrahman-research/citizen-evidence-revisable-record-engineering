from copy import deepcopy

import pytest

from record_engineering.replay import replay

NAMES = (
    "VALID",
    "REVISE",
    "WITHDRAW",
    "EXPIRE",
    "SELFCHECK",
    "HASH",
    "STALE",
    "CONTRADICT",
    "INCONCLUSIVE",
    "CLAIMGATE",
    "EMPTY",
    "FUTURE",
    "REPLACECORR",
    "UNAUTH",
    "BOUNDARY",
    "MISSING",
)


@pytest.mark.parametrize("name", NAMES)
def test_named_failure_and_success_paths(base, name):
    rid = "OPS_" + name
    expected = base[5]["operations"][rid]
    r = next(r for r in base[3]["records"] if r["record_id"] == rid)
    assert r["status"] == expected["status"]
    if "claim_id" in expected:
        c = next(c for c in base[3]["claims"] if c["claim_id"] == expected["claim_id"])
        assert c["status"] == expected["claim_status"]


@pytest.mark.parametrize(
    "target",
    [
        "empirical_finding",
        "scientific_validity",
        "lawful_authority",
        "successful_remedy",
        "causal_effect",
        "probability_of_truth",
        "unlisted_target",
    ],
)
def test_unknown_and_escalated_claims_are_blocked(base, target):
    c = next(c for c in base[3]["claims"] if c["target"] == target)
    assert c["status"] == "BLOCKED" and c["reason"] == "target_not_allowlisted"
    assert not any(
        c[k]
        for k in (
            "empirical_finding",
            "causal_effect",
            "lawful_authority",
            "successful_remedy",
        )
    )


def test_prior_support_is_revisable(base):
    before = replay(base[0], "2026-01-27T00:00:00Z")
    cid = base[5]["operations"]["OPS_REVISE"]["claim_id"]
    assert (
        next(c for c in before["claims"] if c["claim_id"] == cid)["status"] == "ACTIVE"
    )
    assert (
        next(c for c in base[3]["claims"] if c["claim_id"] == cid)["status"]
        == "SUPERSEDED"
    )


def test_expiry_is_exclusive_at_exact_boundary(base):
    before = replay(base[0], "2026-01-30T23:59:59Z")
    exact = replay(base[0], "2026-01-31T00:00:00Z")
    rid = "OPS_EXPIRE"
    assert (
        next(r for r in before["records"] if r["record_id"] == rid)["status"]
        == "CORRECTION_RECORDED"
    )
    assert (
        next(r for r in exact["records"] if r["record_id"] == rid)["status"]
        == "VERIFICATION_EXPIRED"
    )


def test_idempotent_redelivery(base, bundle):
    bundle["events"].append(deepcopy(bundle["events"][0]))
    result = replay(bundle, base[1]["default_as_of"])
    assert (
        result["records"] == base[3]["records"]
        and result["claims"] == base[3]["claims"]
    )
    assert sum(r["status"] == "DUPLICATE" for r in result["audit"]) == 2


def test_unknown_revision_does_not_start_record(bundle, base):
    e = next(
        e
        for e in bundle["events"]
        if e["record_id"] == "OPS_HASH" and e["kind"] == "EVIDENCE"
    )
    e["version"] = 3
    result = replay(bundle, base[1]["default_as_of"])
    assert (
        next(r for r in result["records"] if r["record_id"] == "OPS_HASH")["status"]
        == "EMPTY"
    )
    assert (
        next(a for a in result["audit"] if a["event_id"] == e["event_id"])["reason"]
        == "nonconsecutive_revision"
    )


def test_verification_at_own_expiry_is_rejected(bundle, base):
    e = next(
        e
        for e in bundle["events"]
        if e["record_id"] == "OPS_INCONCLUSIVE" and e["kind"] == "VERIFY"
    )
    e["payload"]["expires_at"] = e["recorded_at"]
    result = replay(bundle, base[1]["default_as_of"])
    assert (
        next(a for a in result["audit"] if a["event_id"] == e["event_id"])["reason"]
        == "nonfuture_verification_expiry"
    )


def test_future_arrivals_do_not_apply_before_known(base):
    assert base[3]["future_events_excluded"] == 2
    later = replay(base[0], "2026-02-06T00:00:00Z")
    assert later["future_events_excluded"] == 0
    assert (
        next(r for r in later["records"] if r["record_id"] == "OPS_FUTURE")["status"]
        == "VERIFIED_SUPPORTED"
    )


def test_inconclusive_verification_is_only_recorded_outcome(base):
    r = next(r for r in base[3]["records"] if r["record_id"] == "OPS_INCONCLUSIVE")
    assert r["outcome"] == "INCONCLUSIVE" and not r["correction_event_id"]
    assert not any(
        c["status"] == "ACTIVE"
        and c["target"] == "correction_recorded"
        and c["record_id"] == r["record_id"]
        for c in base[3]["claims"]
    )

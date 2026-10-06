from __future__ import annotations

from .contracts import TARGETS, evidence_hash, instant, validate_bundle


def _claim_gate(e, s, actors):
    p = e["payload"]
    if "REPORTER" not in actors[e["actor_id"]]:
        return "unauthorized_actor"
    if p["target"] not in TARGETS:
        return "target_not_allowlisted"
    if p["target"] == "record_present":
        return (
            ""
            if not p["verification_event_id"] and not p["correction_event_id"]
            else "extraneous_witness"
        )
    if (
        not s["verification_event_id"]
        or p["verification_event_id"] != s["verification_event_id"]
    ):
        return "verification_witness_mismatch"
    if s["expires_at"] <= e["recorded_at"]:
        return "verification_expired"
    if p["target"] == "verification_recorded":
        return "" if not p["correction_event_id"] else "extraneous_witness"
    if (
        s["outcome"] != "SUPPORTED"
        or not s["correction_event_id"]
        or p["correction_event_id"] != s["correction_event_id"]
    ):
        return "correction_witness_mismatch"
    return ""


def replay(bundle, as_of):
    validate_bundle(bundle)
    as_of = instant(as_of)
    actors = {r["actor_id"]: set(r["roles"]) for r in bundle["actors"]}
    states = {}
    for r in bundle["records"]:
        if r["observed_at"] <= as_of:
            states[r["record_id"]] = {
                **r,
                "max_version": 0,
                "evidence_version": None,
                "evidence_event_id": "",
                "evidence_hash": "",
                "signals": None,
                "withdrawn": False,
                "verification_event_id": "",
                "outcome": "",
                "expires_at": "",
                "correction_event_id": "",
            }
    audit, claims, seen = [], [], set()
    for e in sorted(bundle["events"], key=lambda e: e["seq"]):
        if e["recorded_at"] > as_of:
            continue
        row = {
            k: e[k]
            for k in ("event_id", "seq", "record_id", "kind", "version", "recorded_at")
        }
        if e["event_id"] in seen:
            audit.append({**row, "status": "DUPLICATE", "reason": "exact_redelivery"})
            continue
        seen.add(e["event_id"])
        s, p, reason = states[e["record_id"]], e["payload"], ""
        active = bool(s["evidence_event_id"]) and not s["withdrawn"]
        if e["kind"] == "EVIDENCE":
            if e["actor_id"] != s["submitter_id"]:
                reason = "unauthorized_actor"
            elif e["version"] != s["max_version"] + 1:
                reason = "nonconsecutive_revision"
            else:
                s.update(
                    max_version=e["version"],
                    evidence_version=e["version"],
                    evidence_event_id=e["event_id"],
                    evidence_hash=evidence_hash(e),
                    signals=p,
                    withdrawn=False,
                    verification_event_id="",
                    outcome="",
                    expires_at="",
                    correction_event_id="",
                )
        else:
            if not active:
                reason = "no_active_evidence"
            elif e["version"] != s["evidence_version"]:
                reason = "stale_evidence_version"
            elif p["evidence_hash"] != s["evidence_hash"]:
                reason = "evidence_hash_mismatch"
            elif e["kind"] == "WITHDRAW":
                if e["actor_id"] != s["submitter_id"]:
                    reason = "unauthorized_actor"
                else:
                    s["withdrawn"] = True
                    s.update(
                        verification_event_id="",
                        outcome="",
                        expires_at="",
                        correction_event_id="",
                    )
            elif e["kind"] == "VERIFY":
                if (
                    "VERIFIER" not in actors[e["actor_id"]]
                    or e["actor_id"] == s["submitter_id"]
                ):
                    reason = "verifier_not_independent"
                elif p["expires_at"] <= e["recorded_at"]:
                    reason = "nonfuture_verification_expiry"
                else:
                    s.update(
                        verification_event_id=e["event_id"],
                        outcome=p["outcome"],
                        expires_at=p["expires_at"],
                        correction_event_id="",
                    )
            elif e["kind"] == "CORRECT":
                if "OFFICER" not in actors[e["actor_id"]]:
                    reason = "unauthorized_actor"
                elif (
                    not s["verification_event_id"]
                    or p["verification_event_id"] != s["verification_event_id"]
                ):
                    reason = "verification_witness_mismatch"
                elif s["expires_at"] <= e["recorded_at"]:
                    reason = "verification_expired"
                elif s["outcome"] != "SUPPORTED":
                    reason = "verification_not_supporting"
                else:
                    s["correction_event_id"] = e["event_id"]
            elif e["kind"] == "CLAIM":
                reason = _claim_gate(e, s, actors)
        audit.append(
            {
                **row,
                "status": "REJECTED" if reason else "ACCEPTED",
                "reason": reason or "valid_transition",
            }
        )
        if e["kind"] == "CLAIM":
            claims.append(
                {
                    "claim_id": e["event_id"],
                    "record_id": e["record_id"],
                    "version": e["version"],
                    "target": p["target"],
                    "evidence_hash": p["evidence_hash"],
                    "verification_event_id": p["verification_event_id"],
                    "correction_event_id": p["correction_event_id"],
                    "status": "BLOCKED" if reason else "ACTIVE",
                    "reason": reason or "current_witnesses",
                    "empirical_finding": False,
                    "causal_effect": False,
                    "lawful_authority": False,
                    "successful_remedy": False,
                    "synthetic": True,
                }
            )
    # Recompute current claim validity instead of treating an earlier PASS as permanent.
    for c in claims:
        if c["status"] == "BLOCKED":
            continue
        s = states[c["record_id"]]
        if (
            c["version"] != s["evidence_version"]
            or c["evidence_hash"] != s["evidence_hash"]
        ):
            c.update(status="SUPERSEDED", reason="evidence_superseded")
        elif s["withdrawn"]:
            c.update(status="RETRACTED", reason="evidence_withdrawn")
        elif c["target"] != "record_present":
            if c["verification_event_id"] != s["verification_event_id"]:
                c.update(status="RETRACTED", reason="verification_replaced")
            elif s["expires_at"] <= as_of:
                c.update(status="EXPIRED", reason="verification_expired")
            elif (
                c["target"] == "correction_recorded"
                and c["correction_event_id"] != s["correction_event_id"]
            ):
                c.update(status="RETRACTED", reason="correction_replaced")
    rows = []
    for s in sorted(states.values(), key=lambda r: r["record_id"]):
        if not s["evidence_event_id"]:
            status = "EMPTY"
        elif s["withdrawn"]:
            status = "WITHDRAWN"
        elif not s["verification_event_id"]:
            status = "UNVERIFIED"
        elif s["expires_at"] <= as_of:
            status = "VERIFICATION_EXPIRED"
        elif s["correction_event_id"]:
            status = "CORRECTION_RECORDED"
        else:
            status = "VERIFIED_" + s["outcome"]
        rows.append(
            {
                **s,
                "status": status,
                "correction_event_id": s["correction_event_id"]
                if status == "CORRECTION_RECORDED"
                else "",
            }
        )
    return {
        "as_of": as_of,
        "records": rows,
        "audit": audit,
        "claims": claims,
        "future_events_excluded": sum(
            e["recorded_at"] > as_of for e in bundle["events"]
        ),
    }

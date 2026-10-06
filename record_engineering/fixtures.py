"""Fabricated inputs; no empirical, private-study, or authenticated evidence."""

from __future__ import annotations

from copy import deepcopy

from .contracts import evidence_hash, validate_bundle


def generate():
    actors = [
        {
            "actor_id": "SIM_SUBMITTER",
            "roles": ["SUBMITTER", "VERIFIER"],
            "synthetic": True,
        },
        {"actor_id": "SIM_VERIFIER", "roles": ["VERIFIER"], "synthetic": True},
        {"actor_id": "SIM_OFFICER", "roles": ["OFFICER"], "synthetic": True},
        {"actor_id": "SIM_REPORTER", "roles": ["REPORTER"], "synthetic": True},
    ]
    records, events, labels, expectations = [], [], [], {}

    def catalog(rid, split, day, cohort="COHORT_A"):
        records.append(
            {
                "record_id": rid,
                "submitter_id": "SIM_SUBMITTER",
                "cohort": cohort,
                "split": split,
                "observed_at": f"2026-01-{day:02}T00:00:00Z",
                "synthetic": True,
            }
        )

    def event(rid, kind, day, payload, version=1, actor=None):
        actor = (
            actor
            or {
                "EVIDENCE": "SIM_SUBMITTER",
                "WITHDRAW": "SIM_SUBMITTER",
                "VERIFY": "SIM_VERIFIER",
                "CORRECT": "SIM_OFFICER",
                "CLAIM": "SIM_REPORTER",
            }[kind]
        )
        stamp = (
            f"2026-01-{day:02}T08:00:00Z"
            if day <= 31
            else f"2026-02-{day - 31:02}T08:00:00Z"
        )
        e = {
            "event_id": f"EVT{len(events) + 1:05}",
            "seq": 1,
            "recorded_at": stamp,
            "record_id": rid,
            "kind": kind,
            "version": version,
            "actor_id": actor,
            "payload": payload,
            "synthetic": True,
        }
        events.append(e)
        return e

    def evidence(rid, day=22, version=1, values=(70, 60, 55), actor=None):
        return event(
            rid,
            "EVIDENCE",
            day,
            dict(
                zip(("mismatch", "provenance_gap", "source_conflict"), values),
                statement_id=f"FABRICATED:{rid}:{version}",
            ),
            version,
            actor,
        )

    def verify(
        e,
        day=23,
        outcome="SUPPORTED",
        expiry="2026-02-10T00:00:00Z",
        actor=None,
        hash_value=None,
    ):
        return event(
            e["record_id"],
            "VERIFY",
            day,
            {
                "evidence_hash": hash_value or evidence_hash(e),
                "outcome": outcome,
                "expires_at": expiry,
            },
            e["version"],
            actor,
        )

    def correct(e, v, day=24):
        return event(
            e["record_id"],
            "CORRECT",
            day,
            {"evidence_hash": evidence_hash(e), "verification_event_id": v["event_id"]},
            e["version"],
        )

    def claim(e, target="correction_recorded", v=None, c=None, day=25):
        return event(
            e["record_id"],
            "CLAIM",
            day,
            {
                "evidence_hash": evidence_hash(e),
                "target": target,
                "verification_event_id": v["event_id"] if v else "",
                "correction_event_id": c["event_id"] if c else "",
            },
            e["version"],
        )

    for split, n in (("CALIBRATION", 80), ("HOLDOUT", 64)):
        for i in range(n):
            rid = ("CAL" if split == "CALIBRATION" else "HLD") + f"{i:03}"
            day = 2 + i % 8 if split == "CALIBRATION" else 20 + i % 8
            cohort = "COHORT_A" if i % 2 == 0 else "COHORT_B"
            values = ((i * 17 + 7) % 101, (i * 29 + 23) % 101, (i * 41 + 11) % 101)
            original_score = values[0] * 50 + values[1] * 30 + values[2] * 20
            truth = original_score >= 5500
            if i % 19 == 0:
                truth = (
                    not truth
                )  # Deliberate fixture noise; not a calibrated error model.
            if (split == "CALIBRATION" and i >= 76) or (
                split == "HOLDOUT" and i % 17 == 0
            ):
                values = (values[0], None, values[2])
            catalog(rid, split, day, cohort)
            evidence(rid, day, values=values)
            late = i >= 72 if split == "CALIBRATION" else i % 5 == 0
            labels.append(
                {
                    "record_id": rid,
                    "needs_review": truth,
                    "recorded_at": "2026-02-05T00:00:00Z"
                    if late
                    else "2026-01-12T00:00:00Z"
                    if split == "CALIBRATION"
                    else "2026-01-30T00:00:00Z",
                    "synthetic": True,
                }
            )

    names = (
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
    for name in names:
        catalog("OPS_" + name, "OPERATIONS", 22)
    duplicate = None
    for name in names:
        rid = "OPS_" + name
        if name == "EMPTY":
            expectations[rid] = {"status": "EMPTY"}
            continue
        e = evidence(
            rid,
            values=(80, 80, 80)
            if name == "BOUNDARY"
            else (70, None, 55)
            if name == "MISSING"
            else (70, 60, 55),
        )
        if name == "UNAUTH":
            e["actor_id"] = "SIM_REPORTER"
            e = evidence(rid)
            verify(e, actor="SIM_REPORTER")
            event(
                rid,
                "WITHDRAW",
                28,
                {"evidence_hash": evidence_hash(e)},
                actor="SIM_REPORTER",
            )
            expectations[rid] = {"status": "UNVERIFIED"}
        elif name in ("BOUNDARY", "MISSING"):
            expectations[rid] = {"status": "UNVERIFIED"}
        elif name == "SELFCHECK":
            v = verify(e, actor="SIM_SUBMITTER")
            correct(e, v)
            claim(e, "verification_recorded", v=v)
            expectations[rid] = {"status": "UNVERIFIED"}
        elif name == "HASH":
            verify(e, hash_value="0" * 64)
            expectations[rid] = {"status": "UNVERIFIED"}
        elif name == "STALE":
            evidence(rid, day=26, version=2, values=(30, 35, 40))
            verify(e, day=27)
            expectations[rid] = {"status": "UNVERIFIED"}
        elif name == "FUTURE":
            verify(e, day=33)
            expectations[rid] = {"status": "UNVERIFIED"}
        elif name == "INCONCLUSIVE":
            v = verify(e, outcome="INCONCLUSIVE")
            correct(e, v)
            cl = claim(e, "verification_recorded", v=v)
            expectations[rid] = {
                "status": "VERIFIED_INCONCLUSIVE",
                "claim_id": cl["event_id"],
                "claim_status": "ACTIVE",
            }
        else:
            v = verify(
                e,
                expiry="2026-01-31T00:00:00Z"
                if name == "EXPIRE"
                else "2026-02-10T00:00:00Z",
            )
            c = correct(e, v)
            cl = claim(e, v=v, c=c)
            expectations[rid] = {
                "status": "CORRECTION_RECORDED",
                "claim_id": cl["event_id"],
                "claim_status": "ACTIVE",
            }
            if name == "VALID":
                duplicate = v
                claim(e, "record_present")
            elif name == "REVISE":
                e2 = evidence(rid, day=28, version=2, values=(40, 45, 50))
                verify(e, day=29)
                verify(e2, day=33)
                expectations[rid].update(status="UNVERIFIED", claim_status="SUPERSEDED")
            elif name == "WITHDRAW":
                event(rid, "WITHDRAW", 28, {"evidence_hash": evidence_hash(e)})
                expectations[rid].update(status="WITHDRAWN", claim_status="RETRACTED")
            elif name == "EXPIRE":
                expectations[rid].update(
                    status="VERIFICATION_EXPIRED", claim_status="EXPIRED"
                )
            elif name == "CONTRADICT":
                v2 = verify(e, day=28, outcome="CONTRADICTED")
                correct(e, v2, day=29)
                expectations[rid].update(
                    status="VERIFIED_CONTRADICTED", claim_status="RETRACTED"
                )
            elif name == "REPLACECORR":
                correct(e, v, day=28)
                expectations[rid].update(claim_status="RETRACTED")
            elif name == "CLAIMGATE":
                for target in (
                    "empirical_finding",
                    "scientific_validity",
                    "lawful_authority",
                    "successful_remedy",
                    "causal_effect",
                    "probability_of_truth",
                    "unlisted_target",
                ):
                    claim(e, target, v=v, c=c)
                claim(e, "record_present", v=v)
    events.sort(key=lambda row: row["recorded_at"])
    for seq, e in enumerate(events, 1):
        e["seq"] = seq
    events.append(deepcopy(duplicate))
    bundle = {
        "schema_version": "1.0",
        "synthetic": True,
        "actors": actors,
        "records": records,
        "events": events,
        "labels": labels,
    }
    validate_bundle(bundle)
    return bundle, {
        "synthetic": True,
        "as_of": "2026-02-01T00:00:00Z",
        "operations": expectations,
    }

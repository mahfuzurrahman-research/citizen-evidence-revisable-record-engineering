from __future__ import annotations

from pathlib import Path

import duckdb

from .contracts import canonical

ROOT = Path(__file__).resolve().parents[1]


def build_warehouse(path, bundle, snapshot, frozen, evaluation):
    con = duckdb.connect(str(path))

    def table(name, schema, rows):
        con.execute(f"CREATE TABLE {name} ({schema})")
        if rows:
            con.executemany(
                f"INSERT INTO {name} VALUES ({','.join('?' for _ in rows[0])})", rows
            )

    try:
        table(
            "catalog",
            "record_id VARCHAR,submitter_id VARCHAR,cohort VARCHAR,split VARCHAR,observed_at VARCHAR",
            [
                tuple(
                    r[k]
                    for k in (
                        "record_id",
                        "submitter_id",
                        "cohort",
                        "split",
                        "observed_at",
                    )
                )
                for r in bundle["records"]
            ],
        )
        table(
            "actors",
            "actor_id VARCHAR,roles_json JSON",
            [(r["actor_id"], canonical(r["roles"])) for r in bundle["actors"]],
        )
        table(
            "raw_events",
            "event_id VARCHAR,seq BIGINT,record_id VARCHAR,kind VARCHAR,version BIGINT,recorded_at VARCHAR,actor_id VARCHAR,payload_json VARCHAR",
            [
                tuple(
                    e[k]
                    for k in (
                        "event_id",
                        "seq",
                        "record_id",
                        "kind",
                        "version",
                        "recorded_at",
                        "actor_id",
                    )
                )
                + (canonical(e["payload"]),)
                for e in bundle["events"]
            ],
        )
        table(
            "labels",
            "record_id VARCHAR,needs_review BOOLEAN,recorded_at VARCHAR",
            [
                (r["record_id"], r["needs_review"], r["recorded_at"])
                for r in bundle["labels"]
            ],
        )
        table(
            "audit",
            "event_id VARCHAR,status VARCHAR",
            [(r["event_id"], r["status"]) for r in snapshot["audit"]],
        )
        table(
            "projections",
            "record_id VARCHAR,status VARCHAR,version BIGINT,evidence_hash VARCHAR,withdrawn BOOLEAN,verification_event_id VARCHAR,outcome VARCHAR,expires_at VARCHAR,correction_event_id VARCHAR",
            [
                tuple(
                    r[k]
                    for k in (
                        "record_id",
                        "status",
                        "evidence_version",
                        "evidence_hash",
                        "withdrawn",
                        "verification_event_id",
                        "outcome",
                        "expires_at",
                        "correction_event_id",
                    )
                )
                for r in snapshot["records"]
            ],
        )
        table(
            "claims",
            "claim_id VARCHAR,version BIGINT,evidence_hash VARCHAR,verification_event_id VARCHAR,correction_event_id VARCHAR,target VARCHAR,status VARCHAR,empirical_finding BOOLEAN,causal_effect BOOLEAN,lawful_authority BOOLEAN,successful_remedy BOOLEAN,synthetic BOOLEAN",
            [
                tuple(
                    r[k]
                    for k in (
                        "claim_id",
                        "version",
                        "evidence_hash",
                        "verification_event_id",
                        "correction_event_id",
                        "target",
                        "status",
                        "empirical_finding",
                        "causal_effect",
                        "lawful_authority",
                        "successful_remedy",
                        "synthetic",
                    )
                )
                for r in snapshot["claims"]
            ],
        )
        table(
            "decisions",
            "record_id VARCHAR,score_bps INTEGER,route VARCHAR,automatic_correction BOOLEAN,synthetic BOOLEAN",
            [
                tuple(
                    r[k]
                    for k in (
                        "record_id",
                        "score_bps",
                        "route",
                        "automatic_correction",
                        "synthetic",
                    )
                )
                for r in evaluation["decisions"]
            ],
        )
        table(
            "queue",
            "record_id VARCHAR,queue_id VARCHAR,review_required BOOLEAN,wrongdoing_established BOOLEAN,synthetic BOOLEAN",
            [
                tuple(
                    r[k]
                    for k in (
                        "record_id",
                        "queue_id",
                        "review_required",
                        "wrongdoing_established",
                        "synthetic",
                    )
                )
                for r in evaluation["queue"]
            ],
        )
        table(
            "frozen_ids",
            "record_id VARCHAR",
            [(rid,) for rid in frozen["calibration_ids"]],
        )
        c = frozen["contract"]
        table(
            "threshold_grid",
            "threshold_bps INTEGER",
            [(t,) for t in c["candidate_thresholds_bps"]],
        )
        table(
            "cuts",
            "name VARCHAR,stamp VARCHAR",
            [("FREEZE", c["calibration_cutoff"]), ("LIVE", snapshot["as_of"])],
        )
        table(
            "policy",
            "mismatch_weight INTEGER,provenance_weight INTEGER,conflict_weight INTEGER,priority_threshold INTEGER,selected_threshold INTEGER,fn_cost INTEGER,fp_cost INTEGER,min_recall INTEGER,max_review INTEGER,min_labels INTEGER,min_class INTEGER",
            [
                (
                    c["weights"]["mismatch"],
                    c["weights"]["provenance_gap"],
                    c["weights"]["source_conflict"],
                    c["priority_threshold_bps"],
                    frozen["threshold_bps"],
                    c["false_negative_cost"],
                    c["false_positive_cost"],
                    c["minimum_recall_bps"],
                    c["maximum_review_rate_bps"],
                    c["minimum_labels"],
                    c["minimum_class_labels"],
                )
            ],
        )
        fields = (
            "threshold_bps",
            "scorable_records",
            "mature_labels",
            "selected_records",
            "tp",
            "fp",
            "tn",
            "fn",
            "loss",
            "feasible",
        )
        table(
            "candidates",
            "threshold_bps INTEGER,scorable_records BIGINT,mature_labels BIGINT,selected_records BIGINT,tp BIGINT,fp BIGINT,tn BIGINT,fn BIGINT,loss BIGINT,feasible BOOLEAN",
            [tuple(r[k] for k in fields) for r in frozen["candidates"]],
        )
        fields = (
            "split",
            "cohort",
            "total_records",
            "scorable_records",
            "insufficient_signals",
            "mature_labels",
            "pending_labels",
            "selected_records",
            "tp",
            "fp",
            "tn",
            "fn",
            "precision",
            "recall",
            "false_positive_rate",
            "review_rate",
            "label_coverage",
        )
        table(
            "metrics",
            "split VARCHAR,cohort VARCHAR,total_records BIGINT,scorable_records BIGINT,insufficient_signals BIGINT,mature_labels BIGINT,pending_labels BIGINT,selected_records BIGINT,tp BIGINT,fp BIGINT,tn BIGINT,fn BIGINT,precision DOUBLE,recall DOUBLE,false_positive_rate DOUBLE,review_rate DOUBLE,label_coverage DOUBLE",
            [tuple(r[k] for k in fields) for r in evaluation["metrics"]],
        )
        con.execute((ROOT / "sql/records_validation.sql").read_text())
        checks = [
            {"check_name": name, "violations": int(n)}
            for name, n in con.execute(
                "SELECT * FROM record_quality ORDER BY check_name"
            ).fetchall()
        ]
        return {
            "status": "PASS" if all(r["violations"] == 0 for r in checks) else "FAIL",
            "total_checks": len(checks),
            "checks": checks,
        }
    finally:
        con.close()

from __future__ import annotations

import csv
import html
import io
from collections import Counter

from .contracts import canonical

TABLES = {
    "record_audit.csv": (
        "audit",
        (
            "event_id",
            "seq",
            "record_id",
            "kind",
            "version",
            "recorded_at",
            "status",
            "reason",
        ),
    ),
    "records.csv": (
        "records",
        (
            "record_id",
            "split",
            "cohort",
            "status",
            "evidence_version",
            "evidence_event_id",
            "evidence_hash",
            "verification_event_id",
            "outcome",
            "expires_at",
            "correction_event_id",
            "withdrawn",
        ),
    ),
    "claims.csv": (
        "claims",
        (
            "claim_id",
            "record_id",
            "version",
            "target",
            "status",
            "reason",
            "evidence_hash",
            "verification_event_id",
            "correction_event_id",
            "empirical_finding",
            "causal_effect",
            "lawful_authority",
            "successful_remedy",
            "synthetic",
        ),
    ),
    "decisions.csv": (
        "decisions",
        (
            "record_id",
            "split",
            "cohort",
            "version",
            "evidence_hash",
            "score_bps",
            "route",
            "automatic_correction",
            "synthetic",
        ),
    ),
    "threshold_candidates.csv": (
        "candidates",
        (
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
        ),
    ),
    "cohort_metrics.csv": (
        "metrics",
        (
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
            "metric_status",
        ),
    ),
    "review_queue.csv": (
        "queue",
        (
            "queue_id",
            "record_id",
            "split",
            "cohort",
            "version",
            "evidence_hash",
            "score_bps",
            "route",
            "reasons",
            "review_required",
            "wrongdoing_established",
            "synthetic",
        ),
    ),
}


def csv_text(rows, fields):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(
        out, fieldnames=fields, lineterminator="\n", extrasaction="ignore"
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                k: canonical(v) if isinstance(v, (list, dict, bool)) else v
                for k, v in row.items()
                if k in fields
            }
        )
    return out.getvalue()


def table_texts(snapshot, frozen, evaluation):
    data = {**snapshot, **evaluation, "candidates": frozen["candidates"]}
    return {name: csv_text(data[key], fields) for name, (key, fields) in TABLES.items()}


def summary(snapshot, frozen, evaluation, quality):
    return {
        "schema_version": "1.0",
        "synthetic": True,
        "as_of": snapshot["as_of"],
        "calibration_cutoff": frozen["contract"]["calibration_cutoff"],
        "selected_threshold_bps": frozen["threshold_bps"],
        "priority_threshold_bps": frozen["contract"]["priority_threshold_bps"],
        "record_count": len(snapshot["records"]),
        "future_events_excluded": snapshot["future_events_excluded"],
        "states": dict(
            sorted(Counter(r["status"] for r in snapshot["records"]).items())
        ),
        "transitions": dict(
            sorted(Counter(r["status"] for r in snapshot["audit"]).items())
        ),
        "claims": dict(
            sorted(Counter(r["status"] for r in snapshot["claims"]).items())
        ),
        "review_queue_records": len(evaluation["queue"]),
        "metrics": evaluation["metrics"],
        "warehouse_quality": quality,
        "score_is_probability": False,
        "automatic_correction_allowed": False,
        "empirical_finding": False,
        "causal_effect": False,
        "lawful_authority": False,
        "successful_remedy": False,
    }


def render_report(s, frozen):
    h = next(
        m for m in s["metrics"] if m["split"] == "HOLDOUT" and m["cohort"] == "ALL"
    )
    best = frozen["selected"]
    return f"""# Synthetic decision and revisable record audit

Observation: {s["as_of"]}. Threshold frozen at {s["calibration_cutoff"]}.

The score is a declared weighted index, not a probability of truth or wrongdoing.
Review begins at {s["selected_threshold_bps"] / 10000:.2f}; priority review begins at {s["priority_threshold_bps"] / 10000:.2f} (inclusive comparisons).
Calibration cost: {best["loss"]} toy units; false negatives: {best["fn"]}; false positives: {best["fp"]}.

## Held-out descriptive results

| Denominator | Records |
|---|---:|
| All holdout records | {h["total_records"]} |
| Scorable | {h["scorable_records"]} |
| Missing signals | {h["insufficient_signals"]} |
| Scored with mature labels | {h["mature_labels"]} |
| Scored with pending labels | {h["pending_labels"]} |
| Selected for review | {h["selected_records"]} |
| True positives / false positives | {h["tp"]} / {h["fp"]} |
| True negatives / false negatives | {h["tn"]} / {h["fn"]} |

Rates use mature labeled, scorable cases for confusion statistics; review rate uses all scorable cases.
Missing signals never become zero scores. Pending labels never become negative labels.
Cohort tables describe this fabricated fixture and do not establish real population fairness.

## Current record and claim state

Records: {s["record_count"]}. States: {canonical(s["states"])}.
Transitions: {canonical(s["transitions"])}. Future events excluded: {s["future_events_excluded"]}.
Claim history: {canonical(s["claims"])}. Review queue: {s["review_queue_records"]} records.
Independent DuckDB checks: {s["warehouse_quality"]["total_checks"]} ({s["warehouse_quality"]["status"]}).

Allowed claims report record presence, a recorded verification outcome, or a recorded correction.
New evidence supersedes earlier claim support. Withdrawal, replacement and expiry revise current validity.
Distinct actor IDs and hashes are toy controls; they do not authenticate identity, source independence or evidence truth.
No threshold automatically corrects a record. A deferred item is not a determination that no problem exists.
An administrative correction record does not establish successful remedy, lawful authority, causal effects or empirical findings.
Unsigned receipts check consistency and reproducibility, not authenticity or a tamper-proof history.
"""


def render_dashboard(s, evaluation):
    esc = lambda value: html.escape(str(value), quote=True)
    rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{esc(r[k])}</td>"
            for k in ("record_id", "cohort", "score_bps", "route", "reasons")
        )
        + "</tr>"
        for r in evaluation["queue"]
    )
    claim_rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{esc(c[k])}</td>"
            for k in ("claim_id", "record_id", "target", "status", "reason")
        )
        + "</tr>"
        for c in evaluation["claim_history"]
    )
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Citizen Evidence — Synthetic Record Audit</title><style>
body{{font:16px system-ui;max-width:1200px;margin:30px auto;padding:0 20px;color:#182334;background:#f8fafc}}h1,h2{{color:#173856}}
.card{{background:white;border:1px solid #cbd5e1;padding:16px;margin:16px 0;border-radius:8px}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{text-align:left;padding:9px;border-bottom:1px solid #d8e0e9;overflow-wrap:anywhere}}input{{font:inherit;padding:8px;max-width:100%;box-sizing:border-box}}.scroll{{overflow-x:auto}}caption{{text-align:left;padding:12px 0;font-weight:600}}
</style><h1>Citizen Evidence — Synthetic Record Audit</h1>
<p>All records, identities, signals and outcomes are fabricated engineering fixtures.</p>
<div class="card">Observation: {esc(s["as_of"])}<br>Review threshold: {s["selected_threshold_bps"] / 10000:.2f} · Priority: {s["priority_threshold_bps"] / 10000:.2f}<br>
Records: {s["record_count"]} · Queue: {s["review_queue_records"]} · SQL: {esc(s["warehouse_quality"]["status"])}</div>
<div class="card"><strong>Reading this report</strong><p>Scores route review; they are not probabilities of truth. Verification can expire or be replaced. Recorded correction does not establish remedy success. Receipts do not authenticate evidence.</p></div>
<label for="filter">Filter review queue by record, cohort or reason</label><p><input id="filter" type="search" placeholder="Search synthetic records"></p>
<div class="scroll"><table id="queue"><caption>Review queue</caption><thead><tr><th>Record</th><th>Cohort</th><th>Score (basis points)</th><th>Route</th><th>Reasons</th></tr></thead><tbody>{rows}</tbody></table></div>
<div class="scroll"><table><caption>Revisable claim history</caption><thead><tr><th>Claim</th><th>Record</th><th>Target</th><th>Current status</th><th>Reason</th></tr></thead><tbody>{claim_rows}</tbody></table></div>
<script>document.getElementById('filter').addEventListener('input',function(){{let q=this.value.toLowerCase();document.querySelectorAll('#queue tbody tr').forEach(r=>{{r.hidden=!r.textContent.toLowerCase().includes(q)}})}});</script></html>
"""

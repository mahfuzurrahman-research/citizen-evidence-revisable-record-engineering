from __future__ import annotations

from copy import deepcopy

from .contracts import SIGNALS, digest, exact, instant, integer
from .replay import replay


def validate_policy(c):
    exact(
        c,
        (
            "schema_version",
            "synthetic",
            "calibration_cutoff",
            "default_as_of",
            "weights",
            "candidate_thresholds_bps",
            "priority_threshold_bps",
            "false_negative_cost",
            "false_positive_cost",
            "minimum_labels",
            "minimum_class_labels",
            "minimum_cohort_labels",
            "minimum_recall_bps",
            "maximum_review_rate_bps",
            "automatic_correction_allowed",
            "score_is_probability",
        ),
        "policy",
    )
    if (
        c["schema_version"] != "1.0"
        or c["synthetic"] is not True
        or c["automatic_correction_allowed"] is not False
        or c["score_is_probability"] is not False
    ):
        raise ValueError("unsafe decision policy")
    for name in ("calibration_cutoff", "default_as_of"):
        if instant(c[name]) != c[name]:
            raise ValueError("canonical policy timestamps required")
    if c["default_as_of"] < c["calibration_cutoff"]:
        raise ValueError("observation precedes calibration")
    exact(c["weights"], SIGNALS, "weights")
    for value in c["weights"].values():
        integer(value, 1, 100, "weight")
    if sum(c["weights"].values()) != 100:
        raise ValueError("weights must sum to 100")
    grid = c["candidate_thresholds_bps"]
    if not isinstance(grid, list) or not grid:
        raise ValueError("nonempty threshold grid required")
    for value in grid:
        integer(value, 0, 10000, "candidate threshold")
    if grid != sorted(set(grid)):
        raise ValueError("threshold grid must be unique and increasing")
    for name in (
        "priority_threshold_bps",
        "minimum_recall_bps",
        "maximum_review_rate_bps",
    ):
        integer(c[name], 0, 10000, name)
    if c["priority_threshold_bps"] < max(grid):
        raise ValueError("priority threshold must cover the review threshold grid")
    for name in (
        "false_negative_cost",
        "false_positive_cost",
        "minimum_labels",
        "minimum_class_labels",
        "minimum_cohort_labels",
    ):
        integer(c[name], 1, 10**6, name)
    return c


def score_bps(row, weights):
    if (
        row["withdrawn"]
        or row["signals"] is None
        or any(row["signals"][s] is None for s in SIGNALS)
    ):
        return None
    return sum(row["signals"][s] * weights[s] for s in SIGNALS)


def _counts(rows, labels, threshold):
    scored = [r for r in rows if r["score_bps"] is not None]
    labeled = [r for r in scored if r["record_id"] in labels]
    tp = fp = tn = fn = 0
    for r in labeled:
        positive, selected = (
            labels[r["record_id"]]["needs_review"],
            r["score_bps"] >= threshold,
        )
        tp += positive and selected
        fp += not positive and selected
        tn += not positive and not selected
        fn += positive and not selected
    selected = sum(r["score_bps"] >= threshold for r in scored)
    return {
        "total_records": len(rows),
        "scorable_records": len(scored),
        "insufficient_signals": len(rows) - len(scored),
        "mature_labels": len(labeled),
        "pending_labels": len(scored) - len(labeled),
        "selected_records": selected,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "false_positive_rate": fp / (fp + tn) if fp + tn else None,
        "review_rate": selected / len(scored) if scored else None,
        "label_coverage": len(labeled) / len(scored) if scored else None,
    }


def fit_policy(bundle, contract):
    validate_policy(contract)
    cutoff = contract["calibration_cutoff"]
    for r in bundle["records"]:
        if (r["split"] == "CALIBRATION" and r["observed_at"] > cutoff) or (
            r["split"] == "HOLDOUT" and r["observed_at"] <= cutoff
        ):
            raise ValueError("calibration/holdout chronology violation")
    snapshot = replay(bundle, cutoff)
    rows = [
        {**r, "score_bps": score_bps(r, contract["weights"])}
        for r in snapshot["records"]
        if r["split"] == "CALIBRATION"
    ]
    ids = {r["record_id"] for r in rows}
    labels = {
        r["record_id"]: r
        for r in bundle["labels"]
        if r["record_id"] in ids and r["recorded_at"] <= cutoff
    }
    scorable_labels = [
        labels[r["record_id"]]
        for r in rows
        if r["score_bps"] is not None and r["record_id"] in labels
    ]
    positives = sum(r["needs_review"] for r in scorable_labels)
    if (
        len(scorable_labels) < contract["minimum_labels"]
        or min(positives, len(scorable_labels) - positives)
        < contract["minimum_class_labels"]
    ):
        raise ValueError("insufficient mature calibration labels/classes")
    candidates = []
    for threshold in contract["candidate_thresholds_bps"]:
        m = _counts(rows, labels, threshold)
        feasible = (
            m["tp"] * 10000 >= contract["minimum_recall_bps"] * (m["tp"] + m["fn"])
            and m["selected_records"] * 10000
            <= contract["maximum_review_rate_bps"] * m["scorable_records"]
        )
        candidates.append(
            {
                "threshold_bps": threshold,
                **m,
                "loss": contract["false_negative_cost"] * m["fn"]
                + contract["false_positive_cost"] * m["fp"],
                "feasible": feasible,
            }
        )
    feasible = [r for r in candidates if r["feasible"]]
    if not feasible:
        raise ValueError("no threshold meets recall and review-capacity constraints")
    best = min(feasible, key=lambda r: (r["loss"], r["fn"], -r["threshold_bps"]))
    return {
        "schema_version": "1.0",
        "synthetic": True,
        "contract": deepcopy(contract),
        "calibration_fingerprint": digest(
            {
                "cutoff": cutoff,
                "records": rows,
                "labels": sorted(labels.values(), key=lambda r: r["record_id"]),
            }
        ),
        "calibration_ids": sorted(ids),
        "threshold_bps": best["threshold_bps"],
        "selection_rule": "feasible: minimum loss, then fewer false negatives, then higher threshold",
        "candidates": candidates,
        "selected": best,
    }


def evaluate(bundle, snapshot, frozen):
    c, threshold = frozen["contract"], frozen["threshold_bps"]
    if frozen != fit_policy(bundle, c):
        raise ValueError(
            "frozen threshold policy differs from calibration reconstruction"
        )
    if snapshot != replay(bundle, snapshot["as_of"]):
        raise ValueError("snapshot differs from raw event replay")
    if snapshot["as_of"] < c["calibration_cutoff"]:
        raise ValueError("evaluation before threshold freeze")
    decisions = []
    for r in snapshot["records"]:
        score = score_bps(r, c["weights"])
        route = (
            "WITHDRAWN"
            if r["withdrawn"]
            else "INSUFFICIENT_SIGNALS"
            if score is None
            else "PRIORITY_REVIEW"
            if score >= c["priority_threshold_bps"]
            else "REVIEW"
            if score >= threshold
            else "DEFERRED"
        )
        decisions.append(
            {
                "record_id": r["record_id"],
                "split": r["split"],
                "cohort": r["cohort"],
                "version": r["evidence_version"],
                "evidence_hash": r["evidence_hash"],
                "score_bps": score,
                "route": route,
                "automatic_correction": False,
                "synthetic": True,
            }
        )
    labels = {
        r["record_id"]: r
        for r in bundle["labels"]
        if r["recorded_at"] <= snapshot["as_of"]
    }
    metrics = []
    for split in ("CALIBRATION", "HOLDOUT"):
        for cohort in ("ALL", "COHORT_A", "COHORT_B"):
            rows = [
                r
                for r in decisions
                if r["split"] == split and (cohort == "ALL" or r["cohort"] == cohort)
            ]
            m = _counts(rows, labels, threshold)
            metrics.append(
                {
                    "split": split,
                    "cohort": cohort,
                    **m,
                    "metric_status": "DESCRIPTIVE"
                    if m["mature_labels"] >= c["minimum_cohort_labels"]
                    else "INSUFFICIENT_LABELS",
                }
            )
    reasons = {}

    def add(rid, reason):
        reasons.setdefault(rid, set()).add(reason)

    for r, d in zip(snapshot["records"], decisions):
        if r["split"] == "CALIBRATION" or r["withdrawn"]:
            continue
        if r["status"] != "CORRECTION_RECORDED" and d["route"] in (
            "REVIEW",
            "PRIORITY_REVIEW",
            "INSUFFICIENT_SIGNALS",
        ):
            add(r["record_id"], d["route"].lower())
        if r["status"] in (
            "VERIFICATION_EXPIRED",
            "VERIFIED_CONTRADICTED",
            "VERIFIED_INCONCLUSIVE",
            "EMPTY",
        ):
            add(r["record_id"], r["status"].lower())
    for a in snapshot["audit"]:
        if a["status"] == "REJECTED":
            add(a["record_id"], "blocked_" + a["reason"])
    by_id = {r["record_id"]: r for r in decisions}
    queue = [
        {
            **by_id[rid],
            "queue_id": "REVIEW:" + rid,
            "reasons": sorted(rs),
            "review_required": True,
            "wrongdoing_established": False,
        }
        for rid, rs in sorted(reasons.items())
    ]
    return {"decisions": decisions, "metrics": metrics, "queue": queue}

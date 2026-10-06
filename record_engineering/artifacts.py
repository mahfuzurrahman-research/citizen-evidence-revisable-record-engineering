from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import duckdb

from .contracts import canonical, digest, strict_json
from .replay import replay
from .reporting import render_dashboard, render_report, summary, table_texts
from .thresholds import evaluate, fit_policy
from .warehouse import ROOT, build_warehouse

OWNER = "synthetic_revisable_records_v1"
INVENTORY = (
    "inputs.json",
    "fixture_expectations.json",
    "decision_policy.json",
    "frozen_policy.json",
    "snapshot.json",
    "decision_evaluation.json",
    "record_audit.csv",
    "records.csv",
    "claims.csv",
    "decisions.csv",
    "threshold_candidates.csv",
    "cohort_metrics.csv",
    "review_queue.csv",
    "records.duckdb",
    "sql_quality.json",
    "summary.json",
    "report.md",
    "dashboard.html",
    "source_manifest.json",
)


def json_text(obj):
    return canonical(obj) + "\n"


def source_manifest():
    paths = sorted(
        list((ROOT / "record_engineering").glob("*.py"))
        + [
            ROOT / "sql/records_validation.sql",
            ROOT / "contracts/public_decision_policy.json",
            ROOT / "requirements.txt",
        ]
    )
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in paths
    }


def db_fingerprint(path):
    con = duckdb.connect(str(path), read_only=True)
    try:
        result = {}
        for (name,) in con.execute("SHOW TABLES").fetchall():
            quoted = '"' + name.replace('"', '""') + '"'
            rows = con.execute(f"SELECT * FROM {quoted}").fetchall()
            schema = con.execute(f"DESCRIBE {quoted}").fetchall()
            result[name] = {"schema": schema, "rows": sorted(rows, key=canonical)}
        return digest(result)
    finally:
        con.close()


def write_receipt(output, as_of):
    receipt = {
        "owner": OWNER,
        "schema_version": "1.0",
        "synthetic": True,
        "as_of": as_of,
        "artifacts": {
            name: hashlib.sha256((output / name).read_bytes()).hexdigest()
            for name in INVENTORY
        },
        "unsigned": True,
        "authenticity_established": False,
    }
    (output / "run_receipt.json").write_text(json_text(receipt))


def verify_saved(output):
    output = Path(output)
    if output.is_symlink() or not output.is_dir():
        raise ValueError("artifact directory must be a real directory")
    receipt = strict_json((output / "run_receipt.json").read_text())
    if (
        set(receipt)
        != {
            "owner",
            "schema_version",
            "synthetic",
            "as_of",
            "artifacts",
            "unsigned",
            "authenticity_established",
        }
        or receipt["owner"] != OWNER
        or receipt["schema_version"] != "1.0"
        or receipt["synthetic"] is not True
        or receipt["unsigned"] is not True
        or receipt["authenticity_established"] is not False
    ):
        raise ValueError("invalid receipt contract")
    if set(receipt["artifacts"]) != set(INVENTORY) or {
        p.name for p in output.iterdir()
    } != set(INVENTORY) | {"run_receipt.json"}:
        raise ValueError("artifact inventory mismatch")
    for name in INVENTORY:
        p = output / name
        if (
            p.is_symlink()
            or not p.is_file()
            or hashlib.sha256(p.read_bytes()).hexdigest() != receipt["artifacts"][name]
        ):
            raise ValueError(f"artifact hash mismatch: {name}")
    load = lambda name: strict_json((output / name).read_text())
    if load("source_manifest.json") != source_manifest():
        raise ValueError("source fingerprint changed; regenerate artifacts")
    contract = load("decision_policy.json")
    if contract != strict_json(
        (ROOT / "contracts/public_decision_policy.json").read_text()
    ):
        raise ValueError("saved policy differs from source contract")
    bundle = load("inputs.json")
    frozen = fit_policy(bundle, contract)
    snapshot = replay(bundle, receipt["as_of"])
    evaluation = evaluate(bundle, snapshot, frozen)
    for name, expected in (
        ("frozen_policy.json", frozen),
        ("snapshot.json", snapshot),
        ("decision_evaluation.json", evaluation),
    ):
        if load(name) != expected:
            raise ValueError(f"semantic replay mismatch: {name}")
    for name, expected in table_texts(snapshot, frozen, evaluation).items():
        if (output / name).read_text() != expected:
            raise ValueError(f"derived table mismatch: {name}")
    with tempfile.TemporaryDirectory(prefix="record-recheck-") as tmp:
        rebuilt = Path(tmp) / "recheck.duckdb"
        quality = build_warehouse(rebuilt, bundle, snapshot, frozen, evaluation)
        if (
            quality["status"] != "PASS"
            or quality != load("sql_quality.json")
            or db_fingerprint(rebuilt) != db_fingerprint(output / "records.duckdb")
        ):
            raise ValueError("independent warehouse reconstruction mismatch")
    s = summary(snapshot, frozen, evaluation, quality)
    if (
        load("summary.json") != s
        or (output / "report.md").read_text() != render_report(s, frozen)
        or (output / "dashboard.html").read_text()
        != render_dashboard(s, {**evaluation, "claim_history": snapshot["claims"]})
    ):
        raise ValueError("report consistency mismatch")
    return {
        "status": "PASS",
        "artifacts_verified": len(INVENTORY),
        "semantic_replay": True,
        "independent_sql_rebuilt": True,
        "authenticity_established": False,
    }

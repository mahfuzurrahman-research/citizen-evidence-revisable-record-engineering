from __future__ import annotations

import argparse
import fcntl
import shutil
import tempfile
from pathlib import Path

from .artifacts import (
    INVENTORY,
    OWNER,
    json_text,
    source_manifest,
    verify_saved,
    write_receipt,
)
from .contracts import instant, strict_json
from .fixtures import generate
from .replay import replay
from .reporting import render_dashboard, render_report, summary, table_texts
from .thresholds import evaluate, fit_policy
from .warehouse import ROOT, build_warehouse


def _check_destination(output):
    if output.is_symlink():
        raise ValueError("symlink output prohibited")
    if output.exists():
        if not output.is_dir():
            raise ValueError("output must be a directory")
        names = {p.name for p in output.iterdir()}
        if names and (
            names != set(INVENTORY) | {"run_receipt.json"}
            or strict_json((output / "run_receipt.json").read_text()).get("owner")
            != OWNER
        ):
            raise ValueError("refusing to replace an unrecognized output directory")
        if any(p.is_symlink() or not p.is_file() for p in output.iterdir()):
            raise ValueError("unsafe output inventory")


def run_pipeline(output=None, as_of=None):
    output = Path(output) if output is not None else ROOT / "outputs/records"
    if output.is_symlink():
        raise ValueError("symlink output prohibited")
    output = output.absolute()
    output.parent.mkdir(parents=True, exist_ok=True)
    with (output.parent / ("lock-" + output.name)).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        _check_destination(output)
        contract = strict_json(
            (ROOT / "contracts/public_decision_policy.json").read_text()
        )
        as_of = instant(as_of or contract["default_as_of"])
        if as_of < contract["calibration_cutoff"]:
            raise ValueError("observation precedes calibration freeze")
        bundle, expectations = generate()
        frozen = fit_policy(bundle, contract)
        snapshot = replay(bundle, as_of)
        evaluation = evaluate(bundle, snapshot, frozen)
        stage = Path(tempfile.mkdtemp(prefix="record-stage-", dir=output.parent))
        backup = None
        try:
            quality = build_warehouse(
                stage / "records.duckdb", bundle, snapshot, frozen, evaluation
            )
            if quality["status"] != "PASS":
                raise RuntimeError(f"record SQL gates failed: {quality}")
            s = summary(snapshot, frozen, evaluation, quality)
            objects = {
                "inputs.json": bundle,
                "fixture_expectations.json": expectations,
                "decision_policy.json": contract,
                "frozen_policy.json": frozen,
                "snapshot.json": snapshot,
                "decision_evaluation.json": evaluation,
                "sql_quality.json": quality,
                "summary.json": s,
                "source_manifest.json": source_manifest(),
            }
            for name, obj in objects.items():
                (stage / name).write_text(json_text(obj))
            for name, content in table_texts(snapshot, frozen, evaluation).items():
                (stage / name).write_text(content)
            (stage / "report.md").write_text(render_report(s, frozen))
            (stage / "dashboard.html").write_text(
                render_dashboard(s, {**evaluation, "claim_history": snapshot["claims"]})
            )
            write_receipt(stage, as_of)
            verified = verify_saved(stage)
            if output.exists():
                backup = Path(
                    tempfile.mkdtemp(prefix="record-backup-", dir=output.parent)
                )
                backup.rmdir()
                output.rename(backup)
            try:
                stage.rename(output)
            except BaseException:
                if backup is not None:
                    backup.rename(output)
                    backup = None
                raise
            if backup is not None:
                shutil.rmtree(backup)
            return {"status": "PASS", "summary": s, "verification": verified}
        finally:
            if stage.exists():
                shutil.rmtree(stage)


def main():
    parser = argparse.ArgumentParser(
        description="Synthetic threshold and revisable record demo"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/records")
    parser.add_argument("--as-of")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only and args.as_of:
        parser.error("--verify-only uses the saved receipt's observation time")
    result = (
        verify_saved(args.output)
        if args.verify_only
        else run_pipeline(args.output, args.as_of)
    )
    if args.verify_only:
        printed = result
    else:
        s = result["summary"]
        printed = {
            "status": result["status"],
            "as_of": s["as_of"],
            "records": s["record_count"],
            "review_threshold_bps": s["selected_threshold_bps"],
            "review_queue_records": s["review_queue_records"],
            "sql_checks": s["warehouse_quality"]["total_checks"],
            "artifacts_verified": result["verification"]["artifacts_verified"],
        }
    print(json_text(printed), end="")
    print("REVISABLE_RECORDS_STATUS=PASS")


if __name__ == "__main__":
    main()

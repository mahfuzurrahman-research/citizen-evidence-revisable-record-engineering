import hashlib
import shutil
from copy import deepcopy

import duckdb
import pytest

from record_engineering import pipeline
from record_engineering.artifacts import json_text, verify_saved
from record_engineering.contracts import strict_json
from record_engineering.reporting import render_dashboard, summary


@pytest.fixture(scope="module")
def saved(tmp_path_factory):
    path = tmp_path_factory.mktemp("complete") / "records"
    result = pipeline.run_pipeline(path)
    assert result["verification"]["independent_sql_rebuilt"]
    return path


@pytest.fixture
def copy_saved(saved, tmp_path):
    path = tmp_path / "records"
    shutil.copytree(saved, path)
    return path


def update_hash(path, name):
    receipt = strict_json((path / "run_receipt.json").read_text())
    receipt["artifacts"][name] = hashlib.sha256((path / name).read_bytes()).hexdigest()
    (path / "run_receipt.json").write_text(json_text(receipt))


def test_saved_full_receipt_and_sql_rebuild(saved):
    assert verify_saved(saved) == {
        "status": "PASS",
        "artifacts_verified": 19,
        "semantic_replay": True,
        "independent_sql_rebuilt": True,
        "authenticity_established": False,
    }


def test_hash_tamper_detected(copy_saved):
    (copy_saved / "records.csv").write_text("corrupt\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_saved(copy_saved)


def test_rehashed_projection_still_fails_semantic_replay(copy_saved):
    obj = strict_json((copy_saved / "snapshot.json").read_text())
    obj["records"][0]["status"] = "CORRECTION_RECORDED"
    (copy_saved / "snapshot.json").write_text(json_text(obj))
    update_hash(copy_saved, "snapshot.json")
    with pytest.raises(ValueError, match="semantic replay mismatch"):
        verify_saved(copy_saved)


def test_rehashed_database_still_fails_reconstruction(copy_saved):
    con = duckdb.connect(str(copy_saved / "records.duckdb"))
    con.execute("UPDATE projections SET status='CORRUPTED' WHERE record_id='OPS_VALID'")
    con.close()
    update_hash(copy_saved, "records.duckdb")
    with pytest.raises(ValueError, match="warehouse reconstruction mismatch"):
        verify_saved(copy_saved)


def test_rehashed_report_is_checked_against_inputs(copy_saved):
    (copy_saved / "report.md").write_text("successful remedy established\n")
    update_hash(copy_saved, "report.md")
    with pytest.raises(ValueError, match="report consistency"):
        verify_saved(copy_saved)


def test_source_fingerprint_is_required(copy_saved):
    (copy_saved / "source_manifest.json").write_text("{}\n")
    update_hash(copy_saved, "source_manifest.json")
    with pytest.raises(ValueError, match="source fingerprint"):
        verify_saved(copy_saved)


def test_unsigned_receipt_cannot_claim_authenticity(copy_saved):
    r = strict_json((copy_saved / "run_receipt.json").read_text())
    r["authenticity_established"] = True
    (copy_saved / "run_receipt.json").write_text(json_text(r))
    with pytest.raises(ValueError, match="receipt contract"):
        verify_saved(copy_saved)


def test_extra_artifact_is_not_silently_deleted(copy_saved):
    private_note = copy_saved / "user-note.txt"
    private_note.write_text("preserve me")
    with pytest.raises(ValueError, match="unrecognized"):
        pipeline.run_pipeline(copy_saved)
    assert private_note.read_text() == "preserve me"


def test_failed_gate_preserves_prior_success(copy_saved, monkeypatch):
    before = (copy_saved / "run_receipt.json").read_bytes()
    monkeypatch.setattr(
        pipeline, "build_warehouse", lambda *a, **k: {"status": "FAIL", "checks": []}
    )
    with pytest.raises(RuntimeError, match="SQL gates failed"):
        pipeline.run_pipeline(copy_saved)
    assert (copy_saved / "run_receipt.json").read_bytes() == before
    assert not list(copy_saved.parent.glob("record-stage-*"))


def test_symlink_output_is_rejected(saved, tmp_path):
    link = tmp_path / "linked"
    link.symlink_to(saved, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        pipeline.run_pipeline(link)


def test_observation_before_freeze_rejected(tmp_path):
    with pytest.raises(ValueError, match="precedes calibration"):
        pipeline.run_pipeline(tmp_path / "records", "2026-01-01T00:00:00Z")


def test_dashboard_escapes_structured_evidence(base):
    s = summary(base[3], base[2], base[4], {"status": "PASS", "total_checks": 30})
    e = deepcopy(base[4])
    e["claim_history"] = base[3]["claims"]
    e["queue"][0]["record_id"] = '<img src=x onerror="attack()">'
    rendered = render_dashboard(s, e)
    assert "<img src=x" not in rendered and "&lt;img src=x" in rendered


def test_publication_rename_failure_rolls_back(copy_saved, monkeypatch):
    from pathlib import Path

    before = (copy_saved / "run_receipt.json").read_bytes()
    original = Path.rename

    def fail_stage(path, target):
        if path.name.startswith("record-stage-"):
            raise OSError("injected stage rename failure")
        return original(path, target)

    monkeypatch.setattr(Path, "rename", fail_stage)
    with pytest.raises(OSError, match="injected"):
        pipeline.run_pipeline(copy_saved)
    assert (copy_saved / "run_receipt.json").read_bytes() == before
    assert not list(copy_saved.parent.glob("record-backup-*"))

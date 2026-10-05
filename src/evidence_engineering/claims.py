from __future__ import annotations

import csv
import json
from pathlib import Path


def load_boundaries(csv_path: Path) -> list[dict]:
    with Path(csv_path).open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("claim-boundary table is empty")
    return rows


def validate_boundaries(csv_path: Path, contract_path: Path) -> dict:
    rows = load_boundaries(csv_path)
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    if len(rows) != int(contract["required_boundaries"]):
        raise ValueError("unexpected claim-boundary count")
    ids = [r["boundary_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate claim-boundary id")
    if contract["inferred_transitions_allowed"]:
        raise ValueError("public contract must fail closed on inferred transitions")
    return {"status":"PASS","boundary_count":len(rows)}


def assert_claim_allowed(source_concept: str, target_concept: str, rows: list[dict]) -> bool:
    for row in rows:
        if row["source_concept"] == source_concept and row["prohibited_target"] == target_concept:
            raise ValueError(f"prohibited claim transition: {source_concept} -> {target_concept}")
    return True

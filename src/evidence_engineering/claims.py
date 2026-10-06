from __future__ import annotations

import json
from pathlib import Path

from .io import load_rows

ALLOWED_TRANSITIONS = {
    ("synthetic_result", "engineering_evidence"),
    ("technical_validation", "computational_consistency"),
    ("record_presence", "record_presence"),
    ("administrative_action", "action_recorded"),
    ("model_output", "synthetic_output"),
}


def load_boundaries(csv_path: Path) -> list[dict]:
    return load_rows(
        csv_path, ("boundary_id", "source_concept", "prohibited_target", "rule")
    )


def validate_boundaries(csv_path: Path, contract_path: Path) -> dict:
    rows = load_boundaries(csv_path)
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    if len(rows) != int(contract["required_boundaries"]):
        raise ValueError("unexpected claim-boundary count")
    ids = [r["boundary_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate claim-boundary id")
    if any(
        contract[key] is not False
        for key in (
            "inferred_transitions_allowed",
            "empirical_field_findings",
            "causal_effects",
        )
    ):
        raise ValueError("public contract must fail closed on inferred transitions")
    return {"status": "PASS", "boundary_count": len(rows)}


def assert_claim_allowed(
    source_concept: str, target_concept: str, rows: list[dict]
) -> bool:
    for row in rows:
        if (
            row["source_concept"] == source_concept
            and row["prohibited_target"] == target_concept
        ):
            raise ValueError(
                f"prohibited claim transition: {source_concept} -> {target_concept}"
            )
    if (source_concept, target_concept) not in ALLOWED_TRANSITIONS:
        raise ValueError("claim transition is not explicitly allowlisted")
    return True

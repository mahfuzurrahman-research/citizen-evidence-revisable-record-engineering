from __future__ import annotations

import csv
from pathlib import Path

from .model import Scenario, validate_scenario


def load_rows(path: Path, fields) -> list[dict]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if (
            reader.fieldnames is None
            or len(reader.fieldnames) != len(set(reader.fieldnames))
            or set(reader.fieldnames) != set(fields)
        ):
            raise ValueError("exact unique CSV columns required")
        rows = list(reader)
    if not rows:
        raise ValueError("empty CSV table")
    for row in rows:
        if set(row) != set(fields) or any(
            not isinstance(v, str) or not v or v != v.strip() for v in row.values()
        ):
            raise ValueError("blank, ragged or padded CSV row")
    return rows


def load_scenarios(path: Path) -> list[Scenario]:
    out = []
    required = {
        "scenario_id",
        "visibility",
        "verification_rate",
        "correction_rate",
        "eligible_cases",
    }
    seen = set()
    for line, row in enumerate(load_rows(path, required), start=2):
        sid = row["scenario_id"]
        if sid in seen:
            raise ValueError(f"Row {line}: duplicate scenario_id")
        seen.add(sid)
        s = Scenario(
            scenario_id=sid,
            visibility=float(row["visibility"]),
            verification_rate=float(row["verification_rate"]),
            correction_rate=float(row["correction_rate"]),
            eligible_cases=int(row["eligible_cases"]),
        )
        out.append(validate_scenario(s))
    return out

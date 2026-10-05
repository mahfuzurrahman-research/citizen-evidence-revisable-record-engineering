from __future__ import annotations

import csv
from pathlib import Path

from .model import Scenario, validate_scenario


def load_scenarios(path: Path) -> list[Scenario]:
    out = []
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {"scenario_id","visibility","verification_rate","correction_rate","eligible_cases"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing columns: {sorted(missing)}")
        seen = set()
        for line, row in enumerate(reader, start=2):
            sid = (row["scenario_id"] or "").strip()
            if not sid:
                raise ValueError(f"Row {line}: blank scenario_id")
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

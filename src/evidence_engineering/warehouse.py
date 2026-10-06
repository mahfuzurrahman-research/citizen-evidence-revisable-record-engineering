from __future__ import annotations

import csv
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]


def build_warehouse(
    db_path: Path,
    scenario_csv: Path,
    claim_csv: Path,
    verification_rows: list[dict],
    lineage: dict,
    benchmarks: dict,
) -> duckdb.DuckDBPyConnection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    con = duckdb.connect(str(db_path))

    # Create only the empty staging schema first.
    con.execute((ROOT / "sql/schema.sql").read_text(encoding="utf-8"))

    with Path(scenario_csv).open("r", encoding="utf-8", newline="") as f:
        scenarios = list(csv.DictReader(f))
    with Path(claim_csv).open("r", encoding="utf-8", newline="") as f:
        boundaries = list(csv.DictReader(f))

    con.executemany(
        "INSERT INTO staging_scenario VALUES (?, ?, ?, ?, ?)",
        [
            (
                r["scenario_id"],
                float(r["visibility"]),
                float(r["verification_rate"]),
                float(r["correction_rate"]),
                int(r["eligible_cases"]),
            )
            for r in scenarios
        ],
    )

    con.executemany(
        "INSERT INTO staging_claim_boundary VALUES (?, ?, ?, ?)",
        [
            (r["boundary_id"], r["source_concept"], r["prohibited_target"], r["rule"])
            for r in boundaries
        ],
    )

    for vr in verification_rows:
        p = vr["primary"]
        con.execute(
            "INSERT INTO staging_verification VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                vr["scenario_id"],
                vr["status"],
                vr["max_abs_difference"],
                p["visible_expected"],
                p["verified_expected"],
                p["corrected_expected"],
                p["unresolved_expected"],
            ],
        )

    con.executemany(
        "INSERT INTO staging_lineage_node VALUES (?, ?, ?)",
        [(n["node_id"], n["node_type"], n["label"]) for n in lineage["nodes"]],
    )
    con.executemany(
        "INSERT INTO staging_lineage_edge VALUES (?, ?, ?, ?, ?)",
        [
            (
                e["edge_id"],
                e["edge_type"],
                e["source_node"],
                e["target_node"],
                e["explicit"] == "1",
            )
            for e in lineage["edges"]
        ],
    )
    con.executemany(
        "INSERT INTO staging_benchmark VALUES (?, ?, ?, ?)",
        [
            (r["benchmark_id"], r["benchmark_name"], r["synthetic"], r["status"])
            for r in benchmarks["results"]
        ],
    )

    # Build derived relations only after staging data are loaded.
    for rel in [
        "sql/core.sql",
        "sql/marts.sql",
        "sql/quality.sql",
    ]:
        con.execute((ROOT / rel).read_text(encoding="utf-8"))

    return con


def qa_summary(con: duckdb.DuckDBPyConnection) -> dict:
    row = con.execute("""
        SELECT
            COUNT(*) AS total_checks,
            SUM(CASE WHEN violations = 0 THEN 1 ELSE 0 END) AS passed_checks,
            SUM(CASE WHEN violations <> 0 THEN 1 ELSE 0 END) AS failed_checks,
            SUM(violations) AS total_violations
        FROM quality_results
    """).fetchone()

    out = {
        "total_checks": int(row[0]),
        "passed_checks": int(row[1]),
        "failed_checks": int(row[2]),
        "total_violations": int(row[3]),
    }
    out["status"] = (
        "PASS" if out["failed_checks"] == 0 and out["total_violations"] == 0 else "FAIL"
    )
    return out

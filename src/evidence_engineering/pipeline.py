from __future__ import annotations

from pathlib import Path

from .benchmarks import run_benchmarks
from .claims import validate_boundaries
from .io import load_scenarios
from .lineage import build_lineage
from .reporting import write_reports
from .verification import verify_scenario
from .warehouse import build_warehouse, qa_summary


def run_pipeline(root: Path) -> dict:
    root = Path(root)

    scenarios = load_scenarios(root / "data/synthetic/scenarios.csv")
    verification_rows = [verify_scenario(s) for s in scenarios]
    verification = {
        "status": "PASS",
        "scenario_count": len(verification_rows),
        "max_abs_difference": max(r["max_abs_difference"] for r in verification_rows),
    }

    claim = validate_boundaries(
        root / "data/synthetic/claim_boundaries.csv",
        root / "contracts/public_claim_boundary_contract.json",
    )

    lineage = build_lineage(
        root / "data/synthetic/lineage_nodes.csv",
        root / "data/synthetic/lineage_edges.csv",
        root / "contracts/public_lineage_contract.json",
    )

    benchmarks = run_benchmarks(
        root / "contracts/public_benchmark_contract.json",
        root / "data/synthetic/claim_boundaries.csv",
    )

    con = build_warehouse(
        root / "outputs/public_verification.duckdb",
        root / "data/synthetic/scenarios.csv",
        root / "data/synthetic/claim_boundaries.csv",
        verification_rows,
        lineage,
        benchmarks,
    )
    try:
        qa = qa_summary(con)
        if qa["status"] != "PASS":
            raise RuntimeError(f"DuckDB quality gates failed: {qa}")
    finally:
        con.close()

    payload = {
        "verification": verification,
        "claim_boundaries": claim,
        "lineage": {
            "status": lineage["status"],
            "node_count": lineage["node_count"],
            "edge_count": lineage["edge_count"],
        },
        "benchmarks": {
            "status": benchmarks["status"],
            "benchmark_count": benchmarks["benchmark_count"],
            "pass_count": benchmarks["pass_count"],
        },
        "warehouse_quality": qa,
    }

    write_reports(payload, root / "outputs")
    return payload

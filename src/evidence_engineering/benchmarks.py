from __future__ import annotations

import json
from pathlib import Path

from .claims import assert_claim_allowed, load_boundaries
from .io import load_rows
from .lineage import validate_lineage_rows
from .model import Scenario, validate_scenario


def run_benchmarks(contract_path: Path, claim_csv: Path) -> dict:
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    boundaries = load_boundaries(claim_csv)
    data = Path(claim_csv).parent
    nodes = load_rows(data / "lineage_nodes.csv", ("node_id", "node_type", "label"))
    edges = load_rows(
        data / "lineage_edges.csv",
        ("edge_id", "edge_type", "source_node", "target_node", "explicit"),
    )
    lineage_contract = json.loads(
        (Path(contract_path).parent / "public_lineage_contract.json").read_text()
    )
    results = []

    tests = {
        "F01": lambda: validate_scenario(Scenario("x", 1.2, 0.5, 0.5, 10)),
        "F02": lambda: validate_scenario(Scenario("x", 0.5, 1.2, 0.5, 10)),
        "F03": lambda: validate_scenario(Scenario("x", 0.5, 0.5, -0.1, 10)),
        "F04": lambda: validate_scenario(Scenario("x", 0.5, 0.5, 0.5, 0)),
        "F05": lambda: assert_claim_allowed(
            "synthetic_result", "empirical_finding", boundaries
        ),
        "F06": lambda: validate_lineage_rows(
            nodes,
            [{**e, "explicit": "0"} if i == 0 else e for i, e in enumerate(edges)],
            lineage_contract,
        ),
    }

    for spec in contract["benchmarks"]:
        bid = spec["id"]
        if bid not in tests or spec["expected"] != "REJECT":
            raise ValueError("unsupported benchmark contract")
        rejected = False
        try:
            tests[bid]()
        except ValueError:
            rejected = True

        status = "PASS" if rejected and spec["expected"] == "REJECT" else "FAIL"
        results.append(
            {
                "benchmark_id": bid,
                "benchmark_name": spec["name"],
                "synthetic": True,
                "status": status,
            }
        )

    failures = [r for r in results if r["status"] != "PASS"]
    if failures:
        raise ValueError(f"synthetic benchmark failure: {failures}")

    return {
        "status": "PASS",
        "benchmark_count": len(results),
        "pass_count": len(results),
        "results": results,
    }

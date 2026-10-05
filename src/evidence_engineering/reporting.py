from __future__ import annotations

import json
from pathlib import Path


def write_reports(payload: dict, out_dir: Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "audit_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    md = f"""# Public Engineering Audit

## Verification
- Scenarios: {payload['verification']['scenario_count']}
- Status: **{payload['verification']['status']}**
- Maximum primary/verifier difference: {payload['verification']['max_abs_difference']}

## Claim boundaries
- Boundaries checked: {payload['claim_boundaries']['boundary_count']}
- Status: **{payload['claim_boundaries']['status']}**

## Lineage
- Nodes: {payload['lineage']['node_count']}
- Edges: {payload['lineage']['edge_count']}
- Status: **{payload['lineage']['status']}**

## Synthetic failure-mode benchmarks
- Benchmarks: {payload['benchmarks']['benchmark_count']}
- Passed: {payload['benchmarks']['pass_count']}
- Status: **{payload['benchmarks']['status']}**

## DuckDB quality
- Checks: {payload['warehouse_quality']['total_checks']}
- Failed checks: {payload['warehouse_quality']['failed_checks']}
- Status: **{payload['warehouse_quality']['status']}**

## Boundary
This report contains only synthetic public engineering evidence. It is not an empirical result from the private study.
"""
    (out_dir / "audit_report.md").write_text(md, encoding="utf-8")

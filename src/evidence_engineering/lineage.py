from __future__ import annotations

import csv
import json
from pathlib import Path


def build_lineage(nodes_path: Path, edges_path: Path, contract_path: Path) -> dict:
    with Path(nodes_path).open("r", encoding="utf-8", newline="") as f:
        nodes = list(csv.DictReader(f))
    with Path(edges_path).open("r", encoding="utf-8", newline="") as f:
        edges = list(csv.DictReader(f))
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))

    node_ids = [n["node_id"] for n in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise ValueError("duplicate lineage node")
    if len(nodes) != int(contract["expected_node_count"]):
        raise ValueError("unexpected node count")
    if len(edges) != int(contract["expected_edge_count"]):
        raise ValueError("unexpected edge count")

    node_set = set(node_ids)
    for edge in edges:
        if edge["source_node"] not in node_set or edge["target_node"] not in node_set:
            raise ValueError("dangling lineage edge")
        explicit = edge["explicit"] == "1"
        if contract["required_explicit_edges"] and not explicit:
            raise ValueError("non-explicit lineage edge")
        if not contract["inferred_edges_allowed"] and not explicit:
            raise ValueError("inferred edge prohibited")

    return {
        "status":"PASS",
        "node_count":len(nodes),
        "edge_count":len(edges),
        "nodes":nodes,
        "edges":edges,
    }

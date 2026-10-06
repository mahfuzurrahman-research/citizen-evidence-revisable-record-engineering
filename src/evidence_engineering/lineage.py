from __future__ import annotations

import json
from pathlib import Path

from .io import load_rows


def build_lineage(nodes_path: Path, edges_path: Path, contract_path: Path) -> dict:
    nodes = load_rows(nodes_path, ("node_id", "node_type", "label"))
    edges = load_rows(
        edges_path, ("edge_id", "edge_type", "source_node", "target_node", "explicit")
    )
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    return validate_lineage_rows(nodes, edges, contract)


def validate_lineage_rows(nodes, edges, contract):
    if (
        contract["inferred_edges_allowed"] is not False
        or contract["required_explicit_edges"] is not True
    ):
        raise ValueError("explicit-only lineage contract required")

    node_ids = [n["node_id"] for n in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise ValueError("duplicate lineage node")
    if len(nodes) != int(contract["expected_node_count"]):
        raise ValueError("unexpected node count")
    if len(edges) != int(contract["expected_edge_count"]):
        raise ValueError("unexpected edge count")

    node_set = set(node_ids)
    edge_ids = [e["edge_id"] for e in edges]
    if len(edge_ids) != len(set(edge_ids)):
        raise ValueError("duplicate lineage edge")
    adjacency = {nid: [] for nid in node_ids}
    for edge in edges:
        if edge["source_node"] not in node_set or edge["target_node"] not in node_set:
            raise ValueError("dangling lineage edge")
        explicit = edge["explicit"] == "1"
        if contract["required_explicit_edges"] and not explicit:
            raise ValueError("non-explicit lineage edge")
        if not contract["inferred_edges_allowed"] and not explicit:
            raise ValueError("inferred edge prohibited")
        adjacency[edge["source_node"]].append(edge["target_node"])
    visiting, done = set(), set()

    def visit(node):
        if node in visiting:
            raise ValueError("lineage cycle")
        if node in done:
            return
        visiting.add(node)
        for nxt in adjacency[node]:
            visit(nxt)
        visiting.remove(node)
        done.add(node)

    for node in node_ids:
        visit(node)

    return {
        "status": "PASS",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }

from pathlib import Path

import pytest

from record_engineering.contracts import strict_json
from src.evidence_engineering import benchmarks, verification
from src.evidence_engineering.claims import assert_claim_allowed, load_boundaries
from src.evidence_engineering.io import load_rows, load_scenarios
from src.evidence_engineering.lineage import validate_lineage_rows
from src.evidence_engineering.model import Scenario, validate_scenario

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), "0.5"])
def test_non_numeric_or_non_finite_probability(value):
    with pytest.raises(ValueError):
        validate_scenario(Scenario("X", value, 0.5, 0.5, 10))


def test_boolean_population_rejected():
    with pytest.raises(ValueError):
        validate_scenario(Scenario("X", 0.5, 0.5, 0.5, True))


@pytest.mark.parametrize("tolerance", [True, -1, float("inf"), float("nan")])
def test_verifier_tolerance(tolerance):
    with pytest.raises(ValueError):
        verification.verify_scenario(Scenario("X", 0.5, 0.5, 0.5, 10), tolerance)


@pytest.mark.parametrize("change", ["nan", "id", "extra", "finite_disagreement"])
def test_independent_verifier_actually_checks_output(monkeypatch, change):
    original = verification.independent_verify

    def bad(s):
        out = original(s)
        if change == "nan":
            out["corrected_expected"] = float("nan")
        elif change == "id":
            out["scenario_id"] = "OTHER"
        elif change == "extra":
            out["unrecognized"] = 0
        else:
            out["corrected_expected"] += 1
        return out

    monkeypatch.setattr(verification, "independent_verify", bad)
    with pytest.raises(ValueError):
        verification.verify_scenario(Scenario("X", 0.5, 0.5, 0.5, 10))


@pytest.mark.parametrize(
    "text",
    [
        "scenario_id,visibility,verification_rate,correction_rate,eligible_cases,extra\nX,.5,.5,.5,10,0\n",
        "scenario_id,visibility,verification_rate,correction_rate,eligible_cases\n",
        "scenario_id,visibility,verification_rate,correction_rate,eligible_cases\nX,.5,.5,.5\n",
        "scenario_id,visibility,verification_rate,correction_rate,eligible_cases\n X ,.5,.5,.5,10\n",
        "scenario_id,visibility,verification_rate,correction_rate,eligible_cases\nX,nan,.5,.5,10\n",
        "scenario_id,visibility,verification_rate,correction_rate,eligible_cases,visibility\nX,.5,.5,.5,10,.5\n",
    ],
)
def test_malformed_csv_is_rejected(tmp_path, text):
    path = tmp_path / "bad.csv"
    path.write_text(text)
    with pytest.raises(ValueError):
        load_scenarios(path)


def test_legacy_claim_allowlist_blocks_unknown_pairs():
    rows = load_boundaries(ROOT / "data/synthetic/claim_boundaries.csv")
    with pytest.raises(ValueError):
        assert_claim_allowed("unexpected", "lawful_authority", rows)
    assert assert_claim_allowed("synthetic_result", "engineering_evidence", rows)


@pytest.mark.parametrize("change", ["cycle", "duplicate", "dangling", "inferred"])
def test_lineage_failures_use_real_guard(change):
    data = ROOT / "data/synthetic"
    nodes = load_rows(data / "lineage_nodes.csv", ("node_id", "node_type", "label"))
    edges = load_rows(
        data / "lineage_edges.csv",
        ("edge_id", "edge_type", "source_node", "target_node", "explicit"),
    )
    if change == "cycle":
        edges[0]["target_node"] = edges[0]["source_node"]
    elif change == "duplicate":
        edges[-1]["edge_id"] = edges[0]["edge_id"]
    elif change == "dangling":
        edges[0]["target_node"] = "UNKNOWN"
    else:
        edges[0]["explicit"] = "0"
    contract = strict_json(
        (ROOT / "contracts/public_lineage_contract.json").read_text()
    )
    with pytest.raises(ValueError):
        validate_lineage_rows(nodes, edges, contract)


def test_inferred_edge_benchmark_cannot_pass_with_disabled_validator(monkeypatch):
    monkeypatch.setattr(
        benchmarks, "validate_lineage_rows", lambda *a: {"status": "PASS"}
    )
    with pytest.raises(ValueError, match="benchmark failure"):
        benchmarks.run_benchmarks(
            ROOT / "contracts/public_benchmark_contract.json",
            ROOT / "data/synthetic/claim_boundaries.csv",
        )

import unittest
from pathlib import Path
from src.evidence_engineering.lineage import build_lineage

ROOT = Path(__file__).resolve().parents[1]

class TestLineage(unittest.TestCase):
    def test_explicit_lineage(self):
        out = build_lineage(
            ROOT/"data/synthetic/lineage_nodes.csv",
            ROOT/"data/synthetic/lineage_edges.csv",
            ROOT/"contracts/public_lineage_contract.json",
        )
        self.assertEqual(out["status"], "PASS")
        self.assertGreater(out["node_count"], out["edge_count"])

if __name__ == "__main__":
    unittest.main()

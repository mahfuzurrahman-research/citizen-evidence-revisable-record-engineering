import unittest
from pathlib import Path

from src.evidence_engineering.claims import load_boundaries, validate_boundaries, assert_claim_allowed

ROOT = Path(__file__).resolve().parents[1]

class TestClaims(unittest.TestCase):
    def test_contract(self):
        out = validate_boundaries(
            ROOT/"data/synthetic/claim_boundaries.csv",
            ROOT/"contracts/public_claim_boundary_contract.json",
        )
        self.assertEqual(out["status"], "PASS")

    def test_prohibited_escalation_rejected(self):
        rows = load_boundaries(ROOT/"data/synthetic/claim_boundaries.csv")
        with self.assertRaises(ValueError):
            assert_claim_allowed("synthetic_result", "empirical_finding", rows)

if __name__ == "__main__":
    unittest.main()

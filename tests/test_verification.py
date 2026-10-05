import unittest
from src.evidence_engineering.model import Scenario
from src.evidence_engineering.verification import verify_scenario

class TestVerification(unittest.TestCase):
    def test_independent_verifier(self):
        out = verify_scenario(Scenario("X", .4, .7, .8, 25))
        self.assertEqual(out["status"], "PASS")
        self.assertLessEqual(out["max_abs_difference"], 1e-12)

if __name__ == "__main__":
    unittest.main()

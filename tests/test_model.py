import unittest
from src.evidence_engineering.model import Scenario, validate_scenario, primary_compute

class TestModel(unittest.TestCase):
    def test_valid_scenario(self):
        s = Scenario("X", .5, .6, .7, 10)
        self.assertEqual(validate_scenario(s), s)
        out = primary_compute(s)
        self.assertGreaterEqual(out["corrected_expected"], 0)

    def test_invalid_probability_rejected(self):
        with self.assertRaises(ValueError):
            validate_scenario(Scenario("X", 1.1, .6, .7, 10))

    def test_nonpositive_cases_rejected(self):
        with self.assertRaises(ValueError):
            validate_scenario(Scenario("X", .5, .6, .7, 0))

if __name__ == "__main__":
    unittest.main()

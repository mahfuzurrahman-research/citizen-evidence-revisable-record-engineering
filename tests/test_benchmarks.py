import unittest
from pathlib import Path
from src.evidence_engineering.benchmarks import run_benchmarks

ROOT = Path(__file__).resolve().parents[1]

class TestBenchmarks(unittest.TestCase):
    def test_all_expected_failures_are_caught(self):
        out = run_benchmarks(
            ROOT/"contracts/public_benchmark_contract.json",
            ROOT/"data/synthetic/claim_boundaries.csv",
        )
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["benchmark_count"], out["pass_count"])

if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path
from src.evidence_engineering.pipeline import run_pipeline

ROOT = Path(__file__).resolve().parents[1]

class TestPipeline(unittest.TestCase):
    def test_end_to_end(self):
        out = run_pipeline(ROOT)
        self.assertEqual(out["verification"]["status"], "PASS")
        self.assertEqual(out["claim_boundaries"]["status"], "PASS")
        self.assertEqual(out["lineage"]["status"], "PASS")
        self.assertEqual(out["benchmarks"]["status"], "PASS")
        self.assertEqual(out["warehouse_quality"]["status"], "PASS")

if __name__ == "__main__":
    unittest.main()

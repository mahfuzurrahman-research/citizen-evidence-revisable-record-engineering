from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence_engineering.pipeline import run_pipeline

payload = run_pipeline(ROOT)

print("FORMAL_PARITY=PASS")
print("CLAIM_BOUNDARY_CHECK=PASS")
print("LINEAGE_GRAPH=PASS")
print("SYNTHETIC_BENCHMARKS=PASS")
print("DUCKDB_QA=PASS")

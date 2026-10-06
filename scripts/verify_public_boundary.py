from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

forbidden_paths = [
    "manuscript",
    "provenance",
    "results/baseline",
    "results/verification",
    "analysis/baseline",
    "analysis/verification",
    "docs/scientific_history",
]

for rel in forbidden_paths:
    if (ROOT / rel).exists():
        raise SystemExit(f"PRIVATE_PATH_PRESENT={rel}")

# Exact private scientific identifiers/counts are intentionally absent.
patterns = [
    r"\bE0[1-8]\b",
    r"private_(?:lineage|authority)_count\s*[:=]\s*(?:196|162)\b",
    r"historical_22_tests",
    r"scientific_authority_and_supersession",
    r"old_to_new_crosswalk",
]

for p in ROOT.rglob("*"):
    if (
        not p.is_file()
        or ".git" in p.parts
        or ".venv" in p.parts
        or "__pycache__" in p.parts
        or ".pytest_cache" in p.parts
        or p.name == "verify_public_boundary.py"
    ):
        continue
    if p.suffix.lower() in {".png",".jpg",".jpeg",".zip",".duckdb"}:
        continue
    text = p.read_text(encoding="utf-8", errors="ignore")
    for pattern in patterns:
        if re.search(pattern, text, flags=re.I):
            raise SystemExit(f"PRIVATE_PATTERN_FOUND={pattern}::{p.relative_to(ROOT)}")

print("PUBLIC_BOUNDARY_SCAN=PASS")

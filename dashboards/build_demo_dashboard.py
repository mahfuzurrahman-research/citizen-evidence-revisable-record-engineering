from pathlib import Path
import json, html

ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "outputs/audit_summary.json"
if not src.exists():
    raise SystemExit("Run pipeline first")

obj = json.loads(src.read_text(encoding="utf-8"))
v = obj["verification"]
c = obj["claim_boundaries"]
l = obj["lineage"]
b = obj["benchmarks"]
q = obj["warehouse_quality"]

body = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Citizen Evidence — Engineering Demo</title>
<style>
body{{font-family:system-ui,-apple-system,sans-serif;max-width:980px;margin:40px auto;padding:0 20px;line-height:1.5}}
.card{{border:1px solid #ddd;border-radius:12px;padding:18px;margin:14px 0}}
</style>
</head>
<body>
<h1>Citizen Evidence — Research Engineering Demonstration</h1>
<p>All inputs and outputs are synthetic public engineering artifacts.</p>
<div class="card"><h2>Independent verification</h2><p>Scenarios: {v['scenario_count']} · Status: <strong>{html.escape(v['status'])}</strong></p></div>
<div class="card"><h2>Claim boundaries</h2><p>Rules: {c['boundary_count']} · Status: <strong>{html.escape(c['status'])}</strong></p></div>
<div class="card"><h2>Explicit lineage</h2><p>Nodes: {l['node_count']} · Edges: {l['edge_count']} · Status: <strong>{html.escape(l['status'])}</strong></p></div>
<div class="card"><h2>Failure-mode benchmarks</h2><p>Benchmarks: {b['benchmark_count']} · Passed: {b['pass_count']}</p></div>
<div class="card"><h2>DuckDB QA</h2><p>Checks: {q['total_checks']} · Failures: {q['failed_checks']} · Status: <strong>{html.escape(q['status'])}</strong></p></div>
<div class="card"><h2>Boundary</h2><p>This dashboard is engineering evidence only. It contains no private scientific result.</p></div>
</body></html>"""

(ROOT / "outputs/dashboard.html").write_text(body, encoding="utf-8")
print("DASHBOARD=PASS")

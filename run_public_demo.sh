#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
export PYTHONPATH="$PWD:${PYTHONPATH:-}"

mkdir -p outputs

python3 scripts/verify_public_boundary.py
python3 scripts/run_pipeline.py
python3 dashboards/build_demo_dashboard.py
python3 -m unittest discover -s tests -v

printf '\nPUBLIC_ENGINEERING_DEMO=PASS\n'

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m record_engineering.pipeline
python3 -m pytest tests/records -q
python3 scripts/verify_public_boundary.py
printf '\nRECORDS_DEMO_STATUS=PASS\n'

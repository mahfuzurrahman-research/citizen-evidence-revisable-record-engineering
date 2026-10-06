#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
./run_public_demo.sh
./run_records_demo.sh
printf '\nALL_PUBLIC_DEMOS_STATUS=PASS\n'

# Reproducibility

Use Python 3.12 in a POSIX environment (Linux/macOS), or use Docker. The local process lock uses `fcntl`. Install `requirements.txt` (DuckDB 1.5.6 and pytest 9.1.1) and run `./run_all_demos.sh` from any working directory. The original and new demos both execute their test suites, and the final public boundary scan examines generated text artifacts.

The new pipeline defaults to an explicitly fabricated observation time. `--as-of` changes which events and labels are known, while calibration remains frozen at `2026-01-15T00:00:00Z`. Observations before that freeze are rejected by the CLI. `--verify-only` uses the saved receipt time and cannot be combined with `--as-of`.

`outputs/records/` contains 19 inventoried artifacts and `run_receipt.json`. Verification:

1. Requires the exact artifact inventory, regular files and unsigned synthetic receipt contract.
2. Checks every artifact SHA256 and the current implementation/policy source fingerprints.
3. Reconstructs the frozen policy, record replay and evaluation from saved raw inputs.
4. Compares all derived CSVs, JSON objects, report text and dashboard text.
5. Rebuilds the independent SQL warehouse and compares complete table schemas and rows with the saved database.

DuckDB file bytes may differ between equivalent builds. A receipt hashes the actual saved file; cross-build database verification compares logical contents rather than promising deterministic binary bytes. Reports and semantic tables are deterministic for identical inputs, policy and observation time.

Receipts are unsigned. A coherent rewrite of inputs, code and receipts is not authenticated by these controls. There is no external trust anchor, secure identity check, append-only service or tamper-proof ledger.

The pipeline uses a process lock and a sibling staging directory. It validates the complete staged run before replacement, refuses to overwrite an unrecognized output inventory, and restores the prior directory if the final stage rename fails. A brief directory-swap gap and interrupted-process recovery remain limitations; this is not a crash-durable transaction protocol.

Docker runs `./run_all_demos.sh`. The GitHub workflow runs both demos, builds and executes the container, then uploads only the public outputs. Hosted success must be checked on the corresponding commit; a configured workflow alone is not proof that a run passed.

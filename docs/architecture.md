# Engineering Architecture

Two public demos coexist. The original `src/evidence_engineering` pipeline checks four synthetic arithmetic scenarios, claim transitions, an explicit lineage graph and expected rejection benchmarks in DuckDB. The new `record_engineering` package connects threshold routing to a revisable evidence ledger.

| Module | Responsibility |
|---|---|
| `contracts.py` | Strict JSON/row contracts, UTC timestamps, bounded integer signals and evidence hashes |
| `fixtures.py` | Fabricate calibration, holdout and operational examples; separate test expectations |
| `replay.py` | Replay known events, reject invalid transitions and revise claim support |
| `thresholds.py` | Select a constrained threshold on mature calibration labels; evaluate held-out data |
| `warehouse.py` + `sql/records_validation.sql` | Independently reconstruct the workflow from raw events using DuckDB |
| `reporting.py` | CSV tables, JSON summary, readable report and searchable local dashboard |
| `artifacts.py` | Fixed inventory, source hashes, semantic replay and full database-content reconciliation |
| `pipeline.py` | Stage a complete validated run before replacing a recognized output directory |

The SQL reconstruction does not use Python's accepted/rejected flags to choose evidence, verification, correction or claims. It reconstructs those choices from raw event order, role/catalog rows and witness fields. Source JSON canonicalization is shared at ingestion; DuckDB computes evidence hashes and the subsequent relational checks independently. These are two implementations of one toy specification, not independent empirical evidence.

SQLite, distributed stream processing, ML training, authenticated accounts and external administrative systems are not implemented here. Runtime computation uses Python's standard library and DuckDB; pytest is a test dependency.

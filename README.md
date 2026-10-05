# Citizen Evidence and the Revisable Administrative Record — Research Engineering Demonstration

Public engineering companion for **_Citizen Evidence and the Revisable Administrative Record: Unequal Visibility, Verification and the Limits of Correction_**.

This repository is a **synthetic engineering demonstration**. It does not contain the private manuscript, the paper's exact formal design, historical scientific artifacts, private provenance, empirical data, or the private repository's authoritative results.

## What this repository demonstrates

- deterministic synthetic scenario generation
- an independent verification implementation
- machine-readable claim-boundary contracts
- explicit-only scientific-lineage construction
- synthetic failure-mode benchmarks
- DuckDB staging → core → marts → quality gates
- deterministic JSON and Markdown reporting
- static HTML dashboard generation
- automated unit/integration/failure-mode testing
- GitHub Actions CI
- Docker-based reproducibility
- strict separation between engineering evidence and scientific claims

## Engineering architecture

```text
Synthetic formal scenarios
          │
          ├───────────────┐
          ▼               ▼
 Primary computation   Independent verifier
          │               │
          └───────┬───────┘
                  ▼
           parity / tolerance gate
                  │
        ┌─────────┼──────────┐
        ▼         ▼          ▼
 claim rules   lineage    failure-mode
 contracts      graph      benchmarks
        │         │          │
        └─────────┼──────────┘
                  ▼
          DuckDB warehouse
                  │
          staging / core / marts
                  │
                  ▼
             quality gates
                  │
                  ▼
        JSON / Markdown / dashboard
                  │
                  ▼
              CI + Docker
```

## Quick start

```bash
./run_public_demo.sh
```

Expected markers:

```text
PUBLIC_BOUNDARY_SCAN=PASS
FORMAL_PARITY=PASS
CLAIM_BOUNDARY_CHECK=PASS
LINEAGE_GRAPH=PASS
SYNTHETIC_BENCHMARKS=PASS
DUCKDB_QA=PASS
PUBLIC_ENGINEERING_DEMO=PASS
```

## Public-safe boundary

The public companion intentionally uses:

- fabricated scenarios
- generic concepts
- public-only node/edge identifiers
- synthetic benchmark cases
- generic claim-transition rules

It intentionally excludes:

- the private manuscript
- exact private scenario definitions
- private scientific results
- historical authority/supersession ledgers
- private lineage counts
- private formal parameter values
- recovered historical test identities
- private provenance and release records

## Scientific boundary

A passing engineering test means only that the public software behaves as specified.

It does **not** establish:

- empirical field findings
- causal effects
- lawful administrative authority
- successful administrative remedy
- population representativeness
- real-world deployment effectiveness
- scientific validity of claims outside this public demonstration

## Author

**Mahfuzur Rahman**

Copyright © Mahfuzur Rahman. All rights reserved.

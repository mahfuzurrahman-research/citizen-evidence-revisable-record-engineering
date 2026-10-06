# CV Evidence: Decision Thresholds and Revisable Records

## Supported project wording

**Citizen Evidence and the Revisable Administrative Record — Research Engineering Demonstration**  
Python, DuckDB, pytest, GitHub Actions, Docker; entirely synthetic inputs.

> Built a synthetic evidence-review pipeline with calibration-only threshold selection, held-out evaluation, revision-aware verification and correction records, and a positive claim allowlist. Implemented independent DuckDB reconstruction, temporal and mutation tests, a reasoned review queue, and reproducible audit reports with replay-checked receipts.

A shorter CV bullet:

> Engineered a Python/DuckDB evidence-review workflow with constrained decision thresholds, revisable verification and claim controls, independent SQL reconciliation, automated tests, and CI/container execution on synthetic fixtures.

These statements describe implemented engineering. They do not represent empirical findings from the private paper.

## Reviewable evidence

| Claim | Repository evidence |
|---|---|
| Threshold engineering | `record_engineering/thresholds.py`, `contracts/public_decision_policy.json` |
| Temporal and held-out validation | Calibration/holdout chronology, label availability and leakage tests in `tests/records/test_thresholds.py` |
| Verification and revision controls | `record_engineering/replay.py`, `docs/revisable_records.md` |
| Claim boundaries | Positive record target allowlist, witness/expiry checks, blocked escalation tests |
| Independent SQL validation | `sql/records_validation.sql`, `tests/records/test_sql_reconciliation.py` |
| Artifact reproducibility | `record_engineering/artifacts.py`, `tests/records/test_artifacts.py` |
| Review queue and reports | `record_engineering/reporting.py`; generated CSV, HTML and Markdown artifacts |
| CI and containerization | `.github/workflows/public-validation.yml`, `Dockerfile`, `run_all_demos.sh` |
| Executed local checks | [Validation record](record_validation.md) |

[GitHub Actions](https://github.com/mahfuzurrahman-research/citizen-evidence-revisable-record-engineering/actions) provides hosted run outcomes and downloadable public artifacts. Use the run for the relevant commit when claiming successful CI/container execution.

## Scope limits for a CV or interview

Use **synthetic decision routing**, **threshold validation**, **verification workflow**, **claim integrity**, **SQL reconciliation** and **reproducible engineering**. The score is hand-declared, so do not describe this repo as trained ML, probability calibration or model accuracy on real citizens. Do not claim production deployment, authenticated evidence, tamper-proof records, real fraud detection, lawful authority, scientific replication, causal findings, field fairness or successful administrative remedy.

Fixture precision/recall should be accompanied by the synthetic-data qualifier and mature-label denominator if discussed. Test/gate counts can support engineering evidence; they are not scientific validation counts from the private project. This document supplies wording for a future CV update and does not edit an existing CV.

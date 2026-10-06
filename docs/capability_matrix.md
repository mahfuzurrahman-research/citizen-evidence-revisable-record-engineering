# Capability Matrix

| Skill | Implemented public evidence | Practical limit |
|---|---|---|
| Python engineering | Exact contracts, deterministic fixtures and record state transitions | Synthetic local workflow |
| Threshold selection | Weighted score, constrained candidate sweep and calibration freeze | Hand-declared index; no trained ML model or probability calibration |
| Temporal validation | Separate holdout cohort and label-availability cutoffs | Fabricated chronology |
| Statistical evaluation | Confusion matrices, denominator-aware rates and cohort breakdowns | Descriptive fixture results; no population or fairness inference |
| Verification | Role gates, distinct actor IDs, hashes, versions, explicit outcomes and expiry | Actor IDs and source truth are unauthenticated |
| Claim integrity | Positive allowlist and current witness checks; supersession/retraction/expiry history | Application policy, not legal or scientific authorization |
| Investigation workflow | Stable record queue, reasons, missing-signal and blocked-action routing | No live case management or guilt classification |
| SQL | Raw-event reconstruction, threshold optimization and quality gates | Same synthetic specification; shared canonical input serialization |
| Testing | Negative, temporal, mutation, integration and publication rollback tests | Demonstration-scale coverage |
| Reproducibility | Artifact/source hashes, semantic replay, independent database rebuild | Unsigned receipt; no authenticated or tamper-proof ledger |
| CI and Docker | Both demos and test suites execute in the workflow/container | Check the actual run outcome in GitHub Actions |

[CV evidence](cv_evidence.md) maps these skills to reviewable files and supported wording.

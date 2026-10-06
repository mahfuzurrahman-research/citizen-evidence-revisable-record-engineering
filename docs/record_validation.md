# Executed Validation Record

Local validation date: **2026-10-06**. Runtime: Python 3.12.14, DuckDB 1.5.6, pytest 9.1.1.

## Default fabricated observation

| Item | Observed result |
|---|---:|
| Catalog records | 160 |
| Calibration / holdout / operational records | 80 / 64 / 16 |
| Physical event rows | 210 |
| Future event rows excluded | 2 |
| Accepted / rejected / duplicate consumed events | 188 / 19 / 1 |
| Threshold candidates | 6 |
| Selected review / declared priority thresholds | 0.55 / 0.80 |
| Mature calibration labels usable for selection | 72 |
| Holdout scorable / mature labeled / pending labeled | 60 / 48 / 12 |
| Holdout records with missing signals | 4 |
| Holdout TP / FP / TN / FN | 21 / 1 / 24 / 2 |
| Review queue records | 43 |
| Claim requests | 18 |
| Active / blocked / expired / retracted / superseded claims | 4 / 9 / 1 / 3 / 1 |
| Inventoried artifacts verified | 19 |

The observation time `2026-02-01T00:00:00Z` and calibration cutoff `2026-01-15T00:00:00Z` are fabricated fixture times, not execution dates.

## Checks

The original companion's **nine** unit/integration tests and ten DuckDB quality gates remain in place. The new suite has **166** passing tests, for **175 total**. It exercises strict contracts, temporal boundaries, label leakage, infeasible policies, missing signals, verification/claim lifecycles, raw-event SQL reconciliation, derived mutations, unsigned receipts and publication rollback. No tests were skipped.

The new warehouse has **30 independent quality gates**, for **40 SQL gates total** with the original ten. The combined run also performs the public boundary scan, replays saved artifacts and independently rebuilds the database.

The named operational fixtures include valid correction, replacement evidence, withdrawal, expiry, self-verification rejection, mismatched hashes, stale versions, contradicted/inconclusive verification, blocked claim escalation, an empty record, future verification, correction replacement, unauthorized actions, an inclusive priority threshold and missing signals. Additional tests cover resubmission after withdrawal and observations at multiple time boundaries.

Local Docker was unavailable in the execution environment. The [GitHub Actions workflow](https://github.com/mahfuzurrahman-research/citizen-evidence-revisable-record-engineering/actions) executes both demos on the host and in Docker; inspect its run for the published commit for hosted outcome evidence.

These are engineering checks on fabricated data. Neither passing tests nor agreement with SQL establishes empirical validity, lawful authority, successful remedy or a calibrated real-world decision policy.

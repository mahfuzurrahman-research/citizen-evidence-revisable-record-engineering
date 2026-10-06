# Decision Thresholds and Held-Out Evaluation

## Score and routing

The fixed policy is in `contracts/public_decision_policy.json`. Signals represent fabricated mismatch, provenance-gap and source-conflict indicators, each an integer percentage. Weights are 50, 30 and 20; they sum to 100.

`score_bps = 50*mismatch + 30*provenance_gap + 20*source_conflict`.

The index ranges from 0 to 10,000 basis points. Dividing by 10,000 gives a convenient `[0,1]` display; it does not turn the index into a probability. Any missing required signal yields no score and an `INSUFFICIENT_SIGNALS` route. Withdrawn evidence is not scored.

| Rule | Route |
|---|---|
| Score at or above 8,000 | Priority review |
| Score at or above the frozen review threshold, below priority | Review |
| Score below the review threshold | Deferred |
| Required signal missing or evidence absent | Insufficient signals |
| Evidence withdrawn | Withdrawn |

Comparisons are inclusive. No route automatically verifies evidence, records a correction, establishes wrongdoing or authorizes an expanded claim.

## Threshold selection

Only records explicitly assigned to `CALIBRATION`, observed by `2026-01-15T00:00:00Z`, can tune the threshold. Only their labels recorded by that time can contribute to confusion counts and loss. `HOLDOUT` observations must follow the freeze. Operational scenarios cannot tune it.

The candidate grid is 0.25, 0.35, 0.45, 0.55, 0.65 and 0.75. Synthetic loss is `5*FN + 1*FP`. A feasible candidate must have recall at least 0.75 among mature labeled/scorable calibration records and select no more than 0.65 of **all scorable calibration records**, including those with pending labels. At least 40 mature labels and ten labels in each class are required.

Selection minimizes loss, then false negatives, then favors the higher threshold. An infeasible grid or insufficient labels stops the run; constraints are not silently relaxed. The frozen policy stores all candidates, selected counts and the calibration fingerprint. Evaluation reconstructs both the frozen policy and raw snapshot before accepting them.

The default fixture selects **0.55**, with 30 TP, 1 FP, 38 TN and 3 FN on 72 mature calibration labels; loss is 16 toy units. Calibration has 80 records, of which 76 are scorable and four of those await labels at the freeze.

## Evaluation denominators

The default holdout has 64 records: 60 scorable, four missing signals. At `2026-02-01T00:00:00Z`, 48 scorable records have mature labels and 12 await labels. Counts on mature labels are TP 21, FP 1, TN 24, FN 2. Review routing selects 26 of the 60 scorable records.

Precision, recall and false-positive rate use only mature labeled/scorable cases and their relevant class denominators. Review rate uses all scorable cases. Label coverage is mature labeled/scorable divided by scorable. A zero denominator yields `null`, not a fabricated zero. Cohorts with fewer than ten usable labels receive `INSUFFICIENT_LABELS`; all rates remain descriptive.

Later labels change held-out evaluation without retuning the frozen policy. Missing-label and missing-signal exclusions remain visible. Cohort comparisons are fixture diagnostics and do not prove real population fairness or calibration.

The fixture scores and labels were deliberately constructed to exercise these paths. They are not a trained model, human adjudication dataset or external estimate of discrimination/performance.

## Design reference

The separation between score generation, decision thresholds and held-out evaluation follows the general validation distinction described in the [scikit-learn threshold guide](https://scikit-learn.org/1.8/modules/classification_threshold.html). This repository implements its own small integer-score sweep and does not use `TunedThresholdClassifierCV` or claim cross-validation that is not executed.

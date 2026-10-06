# Revisable Evidence, Verification and Claims

## Log contract

The catalog names fabricated records, submitter IDs, cohorts, splits and observation times. Each event records an explicit sequence, arrival time, record, evidence version, actor, kind and exact payload. Replay consumes only events known at the chosen observation time. It preserves rejected requests and exact duplicate redeliveries in the audit; future requests remain excluded.

Evidence versions are consecutive per record. The submitter may replace an earlier evidence revision with the next version or withdraw the active version. Resubmission after withdrawal requires a new version. A new revision clears active verification and correction support even when some signal values are unchanged.

## Operational gates

| Event | Required control | Result |
|---|---|---|
| `EVIDENCE` | Catalog submitter; next consecutive version | Active evidence revision and payload hash |
| `WITHDRAW` | Catalog submitter; current version/hash | Withdrawn evidence; current verification/correction cleared |
| `VERIFY` | Verifier role; actor differs from submitter; current version/hash; future expiry | Explicit supported, contradicted or inconclusive outcome; prior correction cleared |
| `CORRECT` | Officer role; current hash/version and latest supported, unexpired verification ID | A correction event is recorded |
| `CLAIM` | Reporter role; current evidence witnesses; target-specific current supporting IDs | Narrow claim accepted or explicitly blocked |

New accepted verification replaces prior verification for the same revision. A rejected or stale verification does not overwrite current support. Correction requires `SUPPORTED`; `INCONCLUSIVE` and `CONTRADICTED` cannot authorize it. Verification expires when `as_of >= expires_at`.

These IDs and roles are fabricated application metadata. There is no authentication, independently established source identity or permission service. An officer role in a toy catalog is not lawful administrative authority.

## Claim validity

The allowlist contains only `record_present`, `verification_recorded` and `correction_recorded`. Unknown targets and excess/mismatched witnesses fail closed. `verification_recorded` may describe an inconclusive or contradicted outcome; it does not assert that evidence is supported. The correction target needs an explicit current correction and supporting verification.

Claim requests retain their IDs, versions, hashes, witness references and reasons. Snapshot validity is recomputed:

- `ACTIVE`: current witnesses still support the narrow statement.
- `BLOCKED`: the request failed at the time it arrived.
- `SUPERSEDED`: a later evidence revision replaced the claim's version/hash.
- `RETRACTED`: withdrawal or replacement invalidated current support.
- `EXPIRED`: the referenced current verification reached expiry.

These are current snapshot classifications, not a complete time-indexed legal history. If several later changes apply, evaluation checks evidence replacement, withdrawal, verification replacement, expiry and correction replacement in that order. Earlier requests and subsequent events remain available for replay at another cutoff.

## Review queue

One item per record collects routing, insufficient-signal, expired/contradicted/inconclusive verification and rejected-action reasons. Active correction records are removed from ordinary score-based review routing, while historical blocked requests remain visible. Withdrawn evidence is removed from ordinary routing; a blocked request may still create a review item. No queue item asserts wrongdoing.

The lifecycle draws on generic [W3C PROV-DM](https://www.w3.org/TR/prov-dm/) concepts of entities, revision and invalidation. This local schema is not a PROV export, conformance implementation or the private study's scientific lineage.

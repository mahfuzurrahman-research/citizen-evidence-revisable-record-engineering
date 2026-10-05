# Data Quality

The DuckDB quality layer verifies:

- synthetic scenario parameters are in permitted ranges
- every scenario has a verification record
- independent verification passes within tolerance
- claim-boundary contracts are present
- lineage edges have valid source and target nodes
- lineage edges are explicit, not inferred
- benchmark rows remain explicitly synthetic
- all failure-mode benchmarks pass their expected rejection behavior
- derived outputs remain nonnegative

# Architecture

The public companion separates six engineering concerns:

1. synthetic scenario input
2. primary computation
3. independent verification
4. claim-boundary enforcement
5. explicit-only lineage
6. synthetic failure-mode benchmarking

All public artifacts flow into a DuckDB verification warehouse with staging, core, marts, and executable quality gates.

No private scientific artifact is required to run this repository.

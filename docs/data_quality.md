# Data Quality and Independent Validation

## Input gates

JSON duplicate keys and non-finite constants are rejected. Row schemas require exact fields and explicit synthetic flags. Catalog, label, event and actor IDs must agree. Signal values are integer percentages in `[0,100]`; booleans are rejected as numbers. A missing signal remains `null` and makes the score unavailable.

Timestamps use explicit offsets at whole-second resolution; bundle timestamps must already be canonical UTC. Sequences must agree with nondecreasing arrival times. Equal arrival times use the explicit sequence. Exact event redelivery is idempotent; conflicting event IDs and sequence collisions fail the input gate. Sequence gaps do not establish log completeness.

Malformed inputs stop the run. Well-formed but unauthorized, stale or unsupported operational requests are retained as rejected audit events and cannot change record state. Labels are explicit fabricated references with a recorded availability time; pending labels cannot become negative labels.

## Independent DuckDB gates

`sql/records_validation.sql` reconstructs the following from raw events and source metadata:

- accepted sequential evidence revisions and authorized withdrawal
- current evidence payload hashes and versions
- verification role/identity, witness, replacement and expiry rules
- valid correction and claim witnesses at request time
- current claim support after later revisions, withdrawal, replacement and expiry
- integer scores, routing and queue membership
- calibration membership, candidate confusion counts, cost and feasibility
- selected threshold, cohort denominators, confusion statistics and nullable rates

Output schemas, coverage, duplicate keys, null control fields and claim flags are checked. The warehouse cannot pass solely because Python wrote `PASS`. Mutation tests alter derived projections, witness fields, claims, routing, cost, denominators, rates and queue coverage and assert that specific gates fail.

The original warehouse retains its own ten quality gates. A public boundary scan checks excluded paths and private identifier patterns. Generic numerical values alone are not treated as evidence of a private artifact; contracts and contextual identifiers provide the boundary checks. This scan supplements the fabricated input design and is not a secret-discovery or privacy-proof claim.

## What this proves

The two implementations agree on the declared synthetic workflow at tested cutoffs. They do not independently establish truth, authentic identities, complete real records, representativeness, lawful authority or scientific validity.

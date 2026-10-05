CREATE TABLE staging_scenario (
    scenario_id VARCHAR PRIMARY KEY,
    visibility DOUBLE NOT NULL,
    verification_rate DOUBLE NOT NULL,
    correction_rate DOUBLE NOT NULL,
    eligible_cases INTEGER NOT NULL
);

CREATE TABLE staging_claim_boundary (
    boundary_id VARCHAR PRIMARY KEY,
    source_concept VARCHAR NOT NULL,
    prohibited_target VARCHAR NOT NULL,
    rule VARCHAR NOT NULL
);

CREATE TABLE staging_verification (
    scenario_id VARCHAR PRIMARY KEY,
    status VARCHAR NOT NULL,
    max_abs_difference DOUBLE NOT NULL,
    visible_expected DOUBLE NOT NULL,
    verified_expected DOUBLE NOT NULL,
    corrected_expected DOUBLE NOT NULL,
    unresolved_expected DOUBLE NOT NULL
);

CREATE TABLE staging_lineage_node (
    node_id VARCHAR PRIMARY KEY,
    node_type VARCHAR NOT NULL,
    label VARCHAR NOT NULL
);

CREATE TABLE staging_lineage_edge (
    edge_id VARCHAR PRIMARY KEY,
    edge_type VARCHAR NOT NULL,
    source_node VARCHAR NOT NULL,
    target_node VARCHAR NOT NULL,
    explicit BOOLEAN NOT NULL
);

CREATE TABLE staging_benchmark (
    benchmark_id VARCHAR PRIMARY KEY,
    benchmark_name VARCHAR NOT NULL,
    synthetic BOOLEAN NOT NULL,
    status VARCHAR NOT NULL
);

CREATE TABLE core_scenario AS SELECT * FROM staging_scenario;
CREATE TABLE core_claim_boundary AS SELECT * FROM staging_claim_boundary;
CREATE TABLE core_verification AS SELECT * FROM staging_verification;
CREATE TABLE core_lineage_node AS SELECT * FROM staging_lineage_node;
CREATE TABLE core_lineage_edge AS SELECT * FROM staging_lineage_edge;
CREATE TABLE core_benchmark AS SELECT * FROM staging_benchmark;

CREATE TABLE quality_results AS

SELECT 'scenario_parameters_in_range' AS check_name,
       COUNT(*) AS violations
FROM core_scenario
WHERE visibility < 0 OR visibility > 1
   OR verification_rate < 0 OR verification_rate > 1
   OR correction_rate < 0 OR correction_rate > 1
   OR eligible_cases <= 0

UNION ALL
SELECT 'verification_complete',
       COUNT(*)
FROM core_scenario s
LEFT JOIN core_verification v USING(scenario_id)
WHERE v.scenario_id IS NULL

UNION ALL
SELECT 'verification_passed',
       COUNT(*)
FROM core_verification
WHERE status <> 'PASS' OR max_abs_difference > 1e-12

UNION ALL
SELECT 'claim_boundaries_present',
       CASE WHEN (SELECT COUNT(*) FROM core_claim_boundary) = 5 THEN 0 ELSE 1 END

UNION ALL
SELECT 'lineage_no_dangling_source',
       COUNT(*)
FROM core_lineage_edge e
LEFT JOIN core_lineage_node n ON e.source_node=n.node_id
WHERE n.node_id IS NULL

UNION ALL
SELECT 'lineage_no_dangling_target',
       COUNT(*)
FROM core_lineage_edge e
LEFT JOIN core_lineage_node n ON e.target_node=n.node_id
WHERE n.node_id IS NULL

UNION ALL
SELECT 'lineage_explicit_only',
       COUNT(*)
FROM core_lineage_edge
WHERE NOT explicit

UNION ALL
SELECT 'synthetic_benchmark_flags',
       COUNT(*)
FROM core_benchmark
WHERE NOT synthetic

UNION ALL
SELECT 'synthetic_benchmarks_pass',
       COUNT(*)
FROM core_benchmark
WHERE status <> 'PASS'

UNION ALL
SELECT 'scenario_output_nonnegative',
       COUNT(*)
FROM core_verification
WHERE visible_expected < 0
   OR verified_expected < 0
   OR corrected_expected < 0
   OR unresolved_expected < 0;

CREATE VIEW mart_scenario_verification AS
SELECT
    s.scenario_id,
    s.visibility,
    s.verification_rate,
    s.correction_rate,
    s.eligible_cases,
    v.status,
    v.max_abs_difference,
    v.visible_expected,
    v.verified_expected,
    v.corrected_expected,
    v.unresolved_expected
FROM core_scenario s
JOIN core_verification v USING (scenario_id);

CREATE VIEW mart_lineage_summary AS
SELECT edge_type, COUNT(*) AS edge_count
FROM core_lineage_edge
GROUP BY edge_type;

CREATE VIEW mart_benchmark_health AS
SELECT
    COUNT(*) AS benchmark_count,
    SUM(CASE WHEN status='PASS' THEN 1 ELSE 0 END) AS pass_count,
    SUM(CASE WHEN status<>'PASS' THEN 1 ELSE 0 END) AS fail_count
FROM core_benchmark;

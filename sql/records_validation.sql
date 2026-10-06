-- Independent relational reconstruction from raw events, not Python acceptance flags.
CREATE TABLE events AS SELECT * EXCLUDE (rn) FROM (
  SELECT *, row_number() OVER (PARTITION BY event_id ORDER BY seq) rn FROM raw_events
) WHERE rn=1;

CREATE TABLE accepted_evidence AS
WITH RECURSIVE candidates AS (
  SELECT e.*, row_number() OVER (PARTITION BY e.record_id ORDER BY seq) idx
  FROM events e JOIN catalog r USING(record_id)
  WHERE kind='EVIDENCE' AND e.actor_id=r.submitter_id
), walk(record_id, idx, max_version, accepted) AS (
  SELECT record_id, 0::BIGINT, 0::BIGINT, false FROM catalog
  UNION ALL
  SELECT w.record_id, c.idx,
    CASE WHEN c.version=w.max_version+1 THEN c.version ELSE w.max_version END,
    c.version=w.max_version+1
  FROM walk w JOIN candidates c ON c.record_id=w.record_id AND c.idx=w.idx+1
)
SELECT c.* EXCLUDE(idx), sha256(c.record_id || ':' || c.version::VARCHAR || ':' || c.payload_json) evidence_hash
FROM candidates c JOIN walk w USING(record_id,idx) WHERE w.accepted;

CREATE TABLE evidence_context AS
SELECT e.*, a.event_id evidence_event_id, a.version current_version, a.evidence_hash current_hash, a.seq evidence_seq
FROM events e LEFT JOIN LATERAL (
  SELECT * FROM accepted_evidence a WHERE a.record_id=e.record_id AND a.seq<=e.seq ORDER BY a.seq DESC LIMIT 1
) a ON true;

CREATE TABLE valid_withdraw AS
SELECT e.* FROM evidence_context e JOIN catalog r USING(record_id)
WHERE kind='WITHDRAW' AND actor_id=r.submitter_id AND version=current_version
AND json_extract_string(payload_json,'$.evidence_hash')=current_hash
AND NOT EXISTS (SELECT 1 FROM evidence_context w WHERE w.kind='WITHDRAW'
  AND w.record_id=e.record_id AND w.actor_id=r.submitter_id AND w.version=e.current_version
  AND json_extract_string(w.payload_json,'$.evidence_hash')=e.current_hash
  AND w.seq>e.evidence_seq AND w.seq<e.seq);

CREATE TABLE valid_verify AS
SELECT e.*, json_extract_string(payload_json,'$.outcome') outcome,
  json_extract_string(payload_json,'$.expires_at') expires_at
FROM evidence_context e JOIN catalog r USING(record_id) JOIN actors a USING(actor_id)
WHERE kind='VERIFY' AND json_contains(a.roles_json,'"VERIFIER"') AND e.actor_id<>r.submitter_id
AND version=current_version AND json_extract_string(payload_json,'$.evidence_hash')=current_hash
AND json_extract_string(payload_json,'$.expires_at')>recorded_at
AND NOT EXISTS (SELECT 1 FROM valid_withdraw w WHERE w.record_id=e.record_id AND w.version=e.version AND w.seq>e.evidence_seq AND w.seq<e.seq);

CREATE TABLE verification_context AS
SELECT e.*, v.event_id current_verification_id, v.outcome current_outcome, v.expires_at current_expiry
FROM evidence_context e LEFT JOIN LATERAL (
  SELECT * FROM valid_verify v WHERE v.record_id=e.record_id AND v.version=e.current_version AND v.seq<e.seq ORDER BY v.seq DESC LIMIT 1
) v ON true;

CREATE TABLE valid_correct AS
SELECT e.* FROM verification_context e JOIN actors a USING(actor_id)
WHERE kind='CORRECT' AND json_contains(a.roles_json,'"OFFICER"') AND version=current_version
AND json_extract_string(payload_json,'$.evidence_hash')=current_hash
AND json_extract_string(payload_json,'$.verification_event_id')=current_verification_id
AND current_outcome='SUPPORTED' AND current_expiry>recorded_at
AND NOT EXISTS (SELECT 1 FROM valid_withdraw w WHERE w.record_id=e.record_id AND w.version=e.version AND w.seq>e.evidence_seq AND w.seq<e.seq);

CREATE TABLE valid_claim AS
SELECT e.*, json_extract_string(e.payload_json,'$.target') AS claim_target
FROM verification_context e JOIN actors a USING(actor_id)
LEFT JOIN LATERAL (
  SELECT * FROM valid_correct c WHERE c.record_id=e.record_id AND c.version=e.current_version
  AND c.current_verification_id=e.current_verification_id AND c.seq<e.seq ORDER BY c.seq DESC LIMIT 1
) c ON true
WHERE e.kind='CLAIM' AND json_contains(a.roles_json,'"REPORTER"') AND e.version=e.current_version
AND json_extract_string(e.payload_json,'$.evidence_hash')=e.current_hash
AND NOT EXISTS (SELECT 1 FROM valid_withdraw w WHERE w.record_id=e.record_id AND w.version=e.version AND w.seq>e.evidence_seq AND w.seq<e.seq)
AND (
  (json_extract_string(e.payload_json,'$.target')='record_present'
    AND json_extract_string(e.payload_json,'$.verification_event_id')=''
    AND json_extract_string(e.payload_json,'$.correction_event_id')='')
  OR (json_extract_string(e.payload_json,'$.target')='verification_recorded'
    AND e.current_verification_id IS NOT NULL AND e.current_expiry>e.recorded_at
    AND json_extract_string(e.payload_json,'$.verification_event_id')=e.current_verification_id
    AND json_extract_string(e.payload_json,'$.correction_event_id')='')
  OR (json_extract_string(e.payload_json,'$.target')='correction_recorded'
    AND e.current_outcome='SUPPORTED' AND e.current_expiry>e.recorded_at
    AND json_extract_string(e.payload_json,'$.verification_event_id')=e.current_verification_id
    AND c.event_id IS NOT NULL AND json_extract_string(e.payload_json,'$.correction_event_id')=c.event_id)
);

CREATE TABLE expected_audit AS
SELECT e.event_id, CASE WHEN x.event_id IS NOT NULL THEN 'ACCEPTED' ELSE 'REJECTED' END status
FROM events e LEFT JOIN (
  SELECT event_id FROM accepted_evidence UNION ALL SELECT event_id FROM valid_withdraw
  UNION ALL SELECT event_id FROM valid_verify UNION ALL SELECT event_id FROM valid_correct
  UNION ALL SELECT event_id FROM valid_claim
) x USING(event_id) WHERE e.recorded_at<=(SELECT stamp FROM cuts WHERE name='LIVE');

CREATE TABLE reconstructed AS
SELECT cut.name, r.*, a.version, coalesce(a.evidence_hash,'') evidence_hash, a.payload_json,
  w.event_id IS NOT NULL withdrawn,
  CASE WHEN w.event_id IS NOT NULL THEN '' ELSE coalesce(v.event_id,'') END verification_event_id,
  CASE WHEN w.event_id IS NOT NULL THEN '' ELSE coalesce(v.outcome,'') END outcome,
  CASE WHEN w.event_id IS NOT NULL THEN '' ELSE coalesce(v.expires_at,'') END expires_at,
  CASE WHEN w.event_id IS NULL AND v.expires_at>cut.stamp THEN coalesce(c.event_id,'') ELSE '' END correction_event_id,
  CASE WHEN a.event_id IS NULL THEN 'EMPTY' WHEN w.event_id IS NOT NULL THEN 'WITHDRAWN'
    WHEN v.event_id IS NULL THEN 'UNVERIFIED' WHEN v.expires_at<=cut.stamp THEN 'VERIFICATION_EXPIRED'
    WHEN c.event_id IS NOT NULL THEN 'CORRECTION_RECORDED' ELSE 'VERIFIED_' || v.outcome END status,
  CASE WHEN w.event_id IS NOT NULL THEN NULL ELSE
    json_extract(a.payload_json,'$.mismatch')::INTEGER * p.mismatch_weight
    + json_extract(a.payload_json,'$.provenance_gap')::INTEGER * p.provenance_weight
    + json_extract(a.payload_json,'$.source_conflict')::INTEGER * p.conflict_weight END score_bps
FROM catalog r CROSS JOIN cuts cut CROSS JOIN policy p
LEFT JOIN LATERAL (SELECT * FROM accepted_evidence a WHERE a.record_id=r.record_id AND a.recorded_at<=cut.stamp ORDER BY a.seq DESC LIMIT 1) a ON true
LEFT JOIN LATERAL (SELECT * FROM valid_withdraw w WHERE w.record_id=r.record_id AND w.version=a.version AND w.recorded_at<=cut.stamp ORDER BY w.seq DESC LIMIT 1) w ON true
LEFT JOIN LATERAL (SELECT * FROM valid_verify v WHERE v.record_id=r.record_id AND v.version=a.version AND v.recorded_at<=cut.stamp ORDER BY v.seq DESC LIMIT 1) v ON true
LEFT JOIN LATERAL (SELECT * FROM valid_correct c WHERE c.record_id=r.record_id AND c.version=a.version AND c.current_verification_id=v.event_id AND c.recorded_at<=cut.stamp ORDER BY c.seq DESC LIMIT 1) c ON true
WHERE r.observed_at<=cut.stamp;

CREATE TABLE expected_claims AS
SELECT e.event_id claim_id,
CASE WHEN vc.event_id IS NULL THEN 'BLOCKED'
  WHEN e.version<>r.version OR json_extract_string(e.payload_json,'$.evidence_hash')<>r.evidence_hash THEN 'SUPERSEDED'
  WHEN r.withdrawn THEN 'RETRACTED'
  WHEN vc.claim_target<>'record_present' AND json_extract_string(e.payload_json,'$.verification_event_id')<>r.verification_event_id THEN 'RETRACTED'
  WHEN vc.claim_target<>'record_present' AND r.expires_at<=(SELECT stamp FROM cuts WHERE name='LIVE') THEN 'EXPIRED'
  WHEN vc.claim_target='correction_recorded' AND json_extract_string(e.payload_json,'$.correction_event_id')<>r.correction_event_id THEN 'RETRACTED'
  ELSE 'ACTIVE' END status
FROM events e LEFT JOIN valid_claim vc USING(event_id)
JOIN reconstructed r ON r.record_id=e.record_id AND r.name='LIVE'
WHERE e.kind='CLAIM' AND e.recorded_at<=(SELECT stamp FROM cuts WHERE name='LIVE');

CREATE TABLE expected_decisions AS
SELECT r.*, CASE WHEN withdrawn THEN 'WITHDRAWN' WHEN score_bps IS NULL THEN 'INSUFFICIENT_SIGNALS'
  WHEN score_bps>=p.priority_threshold THEN 'PRIORITY_REVIEW' WHEN score_bps>=p.selected_threshold THEN 'REVIEW' ELSE 'DEFERRED' END route
FROM reconstructed r CROSS JOIN policy p WHERE name='LIVE';

CREATE TABLE expected_candidates AS
WITH counts AS (
SELECT g.threshold_bps,
 count(*) total_records, count(r.score_bps) scorable_records,
 count(*) FILTER (WHERE r.score_bps IS NOT NULL AND l.record_id IS NOT NULL) mature_labels,
 count(*) FILTER (WHERE r.score_bps>=g.threshold_bps) selected_records,
 count(*) FILTER (WHERE r.score_bps>=g.threshold_bps AND l.needs_review) tp,
 count(*) FILTER (WHERE r.score_bps>=g.threshold_bps AND NOT l.needs_review) fp,
 count(*) FILTER (WHERE r.score_bps<g.threshold_bps AND NOT l.needs_review) tn,
 count(*) FILTER (WHERE r.score_bps<g.threshold_bps AND l.needs_review) fn
FROM reconstructed r CROSS JOIN threshold_grid g
LEFT JOIN labels l ON l.record_id=r.record_id AND l.recorded_at<=(SELECT stamp FROM cuts WHERE name='FREEZE')
WHERE r.name='FREEZE' AND r.split='CALIBRATION' GROUP BY g.threshold_bps
)
SELECT c.*, c.fn*p.fn_cost+c.fp*p.fp_cost loss,
  c.tp*10000>=p.min_recall*(c.tp+c.fn) AND c.selected_records*10000<=p.max_review*c.scorable_records feasible
FROM counts c CROSS JOIN policy p;

CREATE TABLE expected_metrics AS
WITH dimensions AS (SELECT s.split,c.cohort FROM (VALUES ('CALIBRATION'),('HOLDOUT')) s(split)
  CROSS JOIN (VALUES ('ALL'),('COHORT_A'),('COHORT_B')) c(cohort)), counts AS (
SELECT d.split,d.cohort,count(r.record_id) total_records,count(r.score_bps) scorable_records,
 count(*) FILTER (WHERE r.score_bps IS NOT NULL AND l.record_id IS NOT NULL) mature_labels,
 count(*) FILTER (WHERE r.score_bps>=p.selected_threshold) selected_records,
 count(*) FILTER (WHERE r.score_bps>=p.selected_threshold AND l.needs_review) tp,
 count(*) FILTER (WHERE r.score_bps>=p.selected_threshold AND NOT l.needs_review) fp,
 count(*) FILTER (WHERE r.score_bps<p.selected_threshold AND NOT l.needs_review) tn,
 count(*) FILTER (WHERE r.score_bps<p.selected_threshold AND l.needs_review) fn
FROM dimensions d CROSS JOIN policy p
LEFT JOIN reconstructed r ON r.name='LIVE' AND r.split=d.split AND (d.cohort='ALL' OR r.cohort=d.cohort)
LEFT JOIN labels l ON l.record_id=r.record_id AND l.recorded_at<=(SELECT stamp FROM cuts WHERE name='LIVE')
GROUP BY d.split,d.cohort)
SELECT *, total_records-scorable_records insufficient_signals,scorable_records-mature_labels pending_labels,
 tp::DOUBLE/nullif(tp+fp,0) AS "precision", tp::DOUBLE/nullif(tp+fn,0) AS recall,
 fp::DOUBLE/nullif(fp+tn,0) AS false_positive_rate,
 selected_records::DOUBLE/nullif(scorable_records,0) AS review_rate,
 mature_labels::DOUBLE/nullif(scorable_records,0) AS label_coverage
FROM counts;

CREATE TABLE expected_queue_ids AS
SELECT record_id FROM expected_decisions WHERE split<>'CALIBRATION' AND NOT withdrawn AND (
 (status<>'CORRECTION_RECORDED' AND route IN ('REVIEW','PRIORITY_REVIEW','INSUFFICIENT_SIGNALS'))
 OR status IN ('VERIFICATION_EXPIRED','VERIFIED_CONTRADICTED','VERIFIED_INCONCLUSIVE','EMPTY'))
UNION SELECT e.record_id FROM expected_audit a JOIN events e USING(event_id) WHERE a.status='REJECTED';

CREATE TABLE record_quality AS
SELECT 'projection_coverage' check_name,count(*) violations FROM reconstructed r FULL JOIN projections x USING(record_id)
 WHERE r.name='LIVE' AND (r.record_id IS NULL OR x.record_id IS NULL)
UNION ALL SELECT 'projection_no_extra',count(*) FROM projections x LEFT JOIN reconstructed r ON r.record_id=x.record_id AND r.name='LIVE' WHERE r.record_id IS NULL
UNION ALL SELECT 'projection_states',count(*) FROM reconstructed r JOIN projections x USING(record_id) WHERE name='LIVE' AND r.status IS DISTINCT FROM x.status
UNION ALL SELECT 'evidence_versions',count(*) FROM reconstructed r JOIN projections x USING(record_id) WHERE name='LIVE' AND r.version IS DISTINCT FROM x.version
UNION ALL SELECT 'evidence_hashes',count(*) FROM reconstructed r JOIN projections x USING(record_id) WHERE name='LIVE' AND r.evidence_hash IS DISTINCT FROM x.evidence_hash
UNION ALL SELECT 'withdrawal_states',count(*) FROM reconstructed r JOIN projections x USING(record_id) WHERE name='LIVE' AND r.withdrawn IS DISTINCT FROM x.withdrawn
UNION ALL SELECT 'verification_witnesses',count(*) FROM reconstructed r JOIN projections x USING(record_id) WHERE name='LIVE' AND (r.verification_event_id,r.outcome,r.expires_at) IS DISTINCT FROM (x.verification_event_id,x.outcome,x.expires_at)
UNION ALL SELECT 'correction_witnesses',count(*) FROM reconstructed r JOIN projections x USING(record_id) WHERE name='LIVE' AND r.correction_event_id IS DISTINCT FROM x.correction_event_id
UNION ALL SELECT 'raw_transition_acceptance',count(*) FROM expected_audit a FULL JOIN (SELECT * FROM audit WHERE status IS DISTINCT FROM 'DUPLICATE') x USING(event_id) WHERE a.event_id IS NULL OR x.event_id IS NULL OR a.status IS DISTINCT FROM x.status
UNION ALL SELECT 'duplicate_idempotency',abs((SELECT count(*) FROM audit WHERE status='DUPLICATE')-(SELECT count(*)-count(DISTINCT event_id) FROM raw_events WHERE recorded_at<=(SELECT stamp FROM cuts WHERE name='LIVE')))
UNION ALL SELECT 'claim_history_coverage',count(*) FROM expected_claims a FULL JOIN claims x USING(claim_id) WHERE a.claim_id IS NULL OR x.claim_id IS NULL
UNION ALL SELECT 'claim_current_validity',count(*) FROM expected_claims a JOIN claims x USING(claim_id) WHERE a.status IS DISTINCT FROM x.status
UNION ALL SELECT 'claim_request_witness_parity',count(*) FROM claims x JOIN events e ON e.event_id=x.claim_id WHERE (x.version,x.evidence_hash,x.verification_event_id,x.correction_event_id,x.target) IS DISTINCT FROM (e.version,json_extract_string(e.payload_json,'$.evidence_hash'),json_extract_string(e.payload_json,'$.verification_event_id'),json_extract_string(e.payload_json,'$.correction_event_id'),json_extract_string(e.payload_json,'$.target'))
UNION ALL SELECT 'claim_boundaries_fail_closed',count(*) FROM claims WHERE empirical_finding IS DISTINCT FROM false OR causal_effect IS DISTINCT FROM false OR lawful_authority IS DISTINCT FROM false OR successful_remedy IS DISTINCT FROM false OR synthetic IS DISTINCT FROM true
UNION ALL SELECT 'active_claim_allowlist',count(*) FROM claims WHERE status='ACTIVE' AND (target IS NULL OR target NOT IN ('record_present','verification_recorded','correction_recorded'))
UNION ALL SELECT 'decision_coverage',count(*) FROM expected_decisions r FULL JOIN decisions x USING(record_id) WHERE r.record_id IS NULL OR x.record_id IS NULL
UNION ALL SELECT 'integer_score_parity',count(*) FROM expected_decisions r JOIN decisions x USING(record_id) WHERE r.score_bps IS DISTINCT FROM x.score_bps
UNION ALL SELECT 'routing_parity',count(*) FROM expected_decisions r JOIN decisions x USING(record_id) WHERE r.route IS DISTINCT FROM x.route
UNION ALL SELECT 'no_automatic_correction',count(*) FROM decisions WHERE automatic_correction IS DISTINCT FROM false OR synthetic IS DISTINCT FROM true
UNION ALL SELECT 'calibration_membership',count(*) FROM (SELECT record_id FROM reconstructed WHERE name='FREEZE' AND split='CALIBRATION') r FULL JOIN frozen_ids x USING(record_id) WHERE r.record_id IS NULL OR x.record_id IS NULL
UNION ALL SELECT 'candidate_coverage',count(*) FROM expected_candidates r FULL JOIN candidates x USING(threshold_bps) WHERE r.threshold_bps IS NULL OR x.threshold_bps IS NULL
UNION ALL SELECT 'candidate_confusion_cost_constraints',count(*) FROM expected_candidates r JOIN candidates x USING(threshold_bps) WHERE (r.scorable_records,r.mature_labels,r.selected_records,r.tp,r.fp,r.tn,r.fn,r.loss,r.feasible) IS DISTINCT FROM (x.scorable_records,x.mature_labels,x.selected_records,x.tp,x.fp,x.tn,x.fn,x.loss,x.feasible)
UNION ALL SELECT 'optimal_feasible_threshold',CASE WHEN (SELECT threshold_bps FROM expected_candidates WHERE feasible ORDER BY loss,fn,threshold_bps DESC LIMIT 1)=(SELECT selected_threshold FROM policy) THEN 0 ELSE 1 END
UNION ALL SELECT 'minimum_calibration_labels',CASE WHEN (SELECT min(mature_labels) FROM expected_candidates)>=(SELECT min_labels FROM policy) AND (SELECT min(tp+fn) FROM expected_candidates)>=(SELECT min_class FROM policy) AND (SELECT min(tn+fp) FROM expected_candidates)>=(SELECT min_class FROM policy) THEN 0 ELSE 1 END
UNION ALL SELECT 'metric_coverage',count(*) FROM expected_metrics r FULL JOIN metrics x USING(split,cohort) WHERE r.split IS NULL OR x.split IS NULL
UNION ALL SELECT 'metric_denominators_and_confusion',count(*) FROM expected_metrics r JOIN metrics x USING(split,cohort) WHERE (r.total_records,r.scorable_records,r.insufficient_signals,r.mature_labels,r.pending_labels,r.selected_records,r.tp,r.fp,r.tn,r.fn) IS DISTINCT FROM (x.total_records,x.scorable_records,x.insufficient_signals,x.mature_labels,x.pending_labels,x.selected_records,x.tp,x.fp,x.tn,x.fn)
UNION ALL SELECT 'metric_rates_and_nulls',count(*) FROM expected_metrics r JOIN metrics x USING(split,cohort) WHERE (r.precision,r.recall,r.false_positive_rate,r.review_rate,r.label_coverage) IS DISTINCT FROM (x.precision,x.recall,x.false_positive_rate,x.review_rate,x.label_coverage)
UNION ALL SELECT 'review_queue_coverage',count(*) FROM expected_queue_ids r FULL JOIN queue x USING(record_id) WHERE r.record_id IS NULL OR x.record_id IS NULL
UNION ALL SELECT 'review_queue_claim_flags',count(*) FROM queue WHERE review_required IS DISTINCT FROM true OR wrongdoing_established IS DISTINCT FROM false OR synthetic IS DISTINCT FROM true OR queue_id IS DISTINCT FROM 'REVIEW:' || record_id
UNION ALL SELECT 'derived_key_integrity',
  (SELECT count(*)-count(DISTINCT record_id) FROM projections)
  +(SELECT count(*)-count(DISTINCT claim_id) FROM claims)
  +(SELECT count(*)-count(DISTINCT record_id) FROM decisions)
  +(SELECT count(*)-count(DISTINCT record_id) FROM queue)
  +(SELECT count(*)-count(DISTINCT threshold_bps) FROM candidates)
  +(SELECT count(*)-count(DISTINCT (split,cohort)) FROM metrics);

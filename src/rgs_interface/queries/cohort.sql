-- AISN cohort: one row per non-test AISN patient. Filters are optional binds.
SELECT
  pad.patient_id                              AS patient_id,
  p.patient_user                              AS patient_name,
  h.name                                      AS hospital_name,
  pad.aisn_group                              AS trial_arm,
  MIN(ct.start_date)                          AS trial_start,
  MAX(ct.end_date)                            AS trial_end,
  (MIN(ct.start_date) <= CURDATE() AND MAX(ct.end_date) >= CURDATE()) AS trial_active,
  MAX(s.STARTING_DATE)                        AS last_session_at,
  DATEDIFF(CURDATE(), MAX(s.STARTING_DATE))   AS days_without_session
FROM patient_aisn_data       AS pad
JOIN patient                 AS p   ON pad.patient_id    = p.patient_id
JOIN hospital                AS h   ON p.hospital_id     = h.hospital_id
JOIN clinical_trials         AS ct  ON pad.patient_id    = ct.patient_id
LEFT JOIN prescription_plus  AS pp  ON pp.PATIENT_ID     = pad.patient_id
LEFT JOIN session_plus       AS s   ON s.PRESCRIPTION_ID = pp.PRESCRIPTION_ID
                                    AND s.STATUS = 'CLOSED'
WHERE h.name <> 'AISN Hospital test'
  AND p.patient_user LIKE 'AI%'
  AND p.patient_user NOT LIKE '%deleted%'
  AND (:patient_id IS NULL OR pad.patient_id = :patient_id)
  AND (:arm IS NULL OR pad.aisn_group = :arm)
  AND (NOT :exclude_control OR pad.aisn_group <> 'Control')
GROUP BY pad.patient_id, p.patient_user, h.name, pad.aisn_group
HAVING (NOT :active OR trial_active = 1)
ORDER BY pad.patient_id;

-- clinical_trials rows. due_today reproduces the production CDSS weekly trigger.
SELECT *
FROM clinical_trials
WHERE (:patient_ids_any = 0 OR PATIENT_ID IN :patient_ids)
  AND (:study_id IS NULL OR STUDY_ID = :study_id)
  AND (NOT :due_today OR (
        RECOMMEND = 1
        AND CURDATE() <= END_DATE
        AND DATEDIFF(CURDATE(), START_DATE) % 7 = 0))
  AND (NOT :with_scores OR CLINICAL_SCORES IS NOT NULL)
ORDER BY PATIENT_ID;

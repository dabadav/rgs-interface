-- CDSS proposals (prescription_staging). patient_ids required; other filters optional.
SELECT
    PRESCRIPTION_STAGING_ID,
    PATIENT_ID,
    PROTOCOL_ID,
    STARTING_DATE,
    ENDING_DATE,
    WEEKDAY,
    SESSION_DURATION,
    RECOMMENDATION_ID,
    WEEKS_SINCE_START,
    STATUS
FROM prescription_staging
WHERE PATIENT_ID IN :patient_ids
  AND (:week IS NULL OR WEEKS_SINCE_START = :week)
  AND (:status IS NULL OR STATUS = :status)
  AND (:recommendation_id IS NULL OR RECOMMENDATION_ID = :recommendation_id)
  AND (:week_start IS NULL OR DATE(STARTING_DATE) = :week_start)
ORDER BY PATIENT_ID, WEEKS_SINCE_START, RECOMMENDATION_ID, PROTOCOL_ID;

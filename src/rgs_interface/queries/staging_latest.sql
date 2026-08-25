-- Latest staged week for a patient and, when :week is given, the most recent
-- RECOMMENDATION_ID written for that week. Always one row.
SELECT
    MAX(WEEKS_SINCE_START) AS max_week,
    (SELECT RECOMMENDATION_ID
       FROM prescription_staging
      WHERE PATIENT_ID = :patient_id AND WEEKS_SINCE_START = :week
      ORDER BY PRESCRIPTION_STAGING_ID DESC
      LIMIT 1) AS latest_recommendation_id
FROM prescription_staging
WHERE PATIENT_ID = :patient_id;

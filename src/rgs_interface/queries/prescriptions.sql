-- Clinician prescriptions (prescription_plus). Optional active-window overlap filter.
SELECT
    PRESCRIPTION_ID,
    PATIENT_ID,
    PROTOCOL_ID,
    STARTING_DATE,
    ENDING_DATE,
    WEEKDAY,
    SESSION_DURATION
FROM prescription_plus
WHERE PATIENT_ID IN :patient_ids
  AND (:active_to   IS NULL OR STARTING_DATE < :active_to)
  AND (:active_from IS NULL OR ENDING_DATE   > :active_from)
ORDER BY PATIENT_ID, STARTING_DATE, PROTOCOL_ID;

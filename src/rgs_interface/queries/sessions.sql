-- Sessions per patient via prescription_plus; optional status and time window.
SELECT
    s.SESSION_ID,
    s.PRESCRIPTION_ID,
    p.PROTOCOL_ID,
    s.STARTING_DATE,
    s.ENDING_DATE,
    s.STATUS
FROM session_plus s
JOIN prescription_plus p ON s.PRESCRIPTION_ID = p.PRESCRIPTION_ID
WHERE p.PATIENT_ID = :patient_id
  AND (:status IS NULL OR s.STATUS = :status)
  AND (:since IS NULL OR s.STARTING_DATE >= :since)
  AND (:until IS NULL OR s.STARTING_DATE <  :until)
ORDER BY s.STARTING_DATE;

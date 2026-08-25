-- Prescription x closed/aborted session x recorded duration, per patient.
SELECT
    pp.PRESCRIPTION_ID,
    pp.PROTOCOL_ID,
    pp.STARTING_DATE,
    pp.WEEKDAY,
    pp.SESSION_DURATION AS PRESCRIBED_DURATION,
    sp.SESSION_ID,
    sp.STARTING_DATE AS SESSION_DATE,
    sp.STATUS AS SESSION_STATUS,
    rec.RECORDED_DURATION
FROM prescription_plus pp
LEFT JOIN session_plus sp
    ON sp.PRESCRIPTION_ID = pp.PRESCRIPTION_ID
    AND sp.STATUS IN ('CLOSED', 'ABORTED')
LEFT JOIN (
    SELECT
        SESSION_ID,
        MAX(CASE WHEN RECORDING_KEY = 'sessionDuration(seconds)' THEN RECORDING_VALUE END) AS RECORDED_DURATION
    FROM recording_plus
    GROUP BY SESSION_ID
) rec ON rec.SESSION_ID = sp.SESSION_ID
WHERE pp.PATIENT_ID = :patient_id
ORDER BY pp.STARTING_DATE, pp.WEEKDAY;

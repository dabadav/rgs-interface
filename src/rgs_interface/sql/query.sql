-- Define a Common Table Expression (CTE) named SessionData
WITH SessionData AS (
    SELECT
        pp.PATIENT_ID,                   -- Patient identifier from prescription
        sp.SESSION_ID,                   -- Session identifier from session table
        pp.PRESCRIPTION_ID,              -- Prescription ID to join back with prescriptions
        pp.PROTOCOL_ID,                  -- Protocol identifier used for the session
        pp.STARTING_DATE AS PRESCRIPTION_STARTING_DATE,
        pp.ENDING_DATE AS PRESCRIPTION_ENDING_DATE,
        pp.WEEKDAY,                      -- Prescribed day of the week for the session
        pp.SESSION_DURATION AS PRESCRIBED_SESSION_DURATION,
        sp.STARTING_DATE AS SESSION_DATE,
        sp.ENDING_DATE,                  -- Actual end time of the session
        TIMESTAMPDIFF(SECOND, sp.STARTING_DATE, sp.ENDING_DATE) AS REAL_SESSION_DURATION, -- Duration in seconds
        sp.STATUS                        -- Session status: CLOSED or ABORTED
    FROM prescription_{rgs_mode} pp
    LEFT JOIN session_{rgs_mode} sp
        ON sp.PRESCRIPTION_ID = pp.PRESCRIPTION_ID
        AND sp.STATUS IN ('CLOSED', 'ABORTED') -- Keep this in ON clause so we don't filter out prescriptions without sessions
)

-- Main query selecting from the above CTE
SELECT
    sd.PATIENT_ID,
    sd.PRESCRIPTION_ID,
    sd.SESSION_ID,
    sd.PROTOCOL_ID,
    sd.PRESCRIPTION_STARTING_DATE,
    sd.PRESCRIPTION_ENDING_DATE,
    sd.SESSION_DATE,
    sd.STATUS,
    
    -- Convert weekday name to index (0 = Monday, ..., 6 = Sunday)
    CASE
        WHEN sd.WEEKDAY = 'MONDAY' THEN 0
        WHEN sd.WEEKDAY = 'TUESDAY' THEN 1
        WHEN sd.WEEKDAY = 'WEDNESDAY' THEN 2
        WHEN sd.WEEKDAY = 'THURSDAY' THEN 3
        WHEN sd.WEEKDAY = 'FRIDAY' THEN 4
        WHEN sd.WEEKDAY = 'SATURDAY' THEN 5
        WHEN sd.WEEKDAY = 'SUNDAY' THEN 6
        ELSE NULL
    END AS WEEKDAY_INDEX,

    sd.REAL_SESSION_DURATION,            -- Actual session duration in seconds
    sd.PRESCRIBED_SESSION_DURATION,      -- Duration that was prescribed

    CAST(r.SESSION_DURATION AS INT) AS SESSION_DURATION, -- Reported duration from the recording table

    -- Adherence metric: ratio of recorded duration to prescribed duration
    CASE
        WHEN sd.PRESCRIBED_SESSION_DURATION > 0 THEN r.SESSION_DURATION / sd.PRESCRIBED_SESSION_DURATION
        ELSE NULL
    END AS ADHERENCE,

    -- Other session outcome metrics
    CAST(r.TOTAL_SUCCESS AS INT) AS TOTAL_SUCCESS,
    CAST(r.TOTAL_ERRORS AS INT) AS TOTAL_ERRORS,
    CAST(r.GAME_SCORE AS INT) AS GAME_SCORE

FROM SessionData sd

-- LEFT JOIN with the recording table (aggregated by SESSION_ID)
LEFT JOIN (
    SELECT
        SESSION_ID,
        MAX(CASE WHEN RECORDING_KEY = 'sessionDuration(seconds)' THEN RECORDING_VALUE END) AS SESSION_DURATION,
        MAX(CASE WHEN RECORDING_KEY = 'totalSuccess' THEN RECORDING_VALUE END) AS TOTAL_SUCCESS,
        MAX(CASE WHEN RECORDING_KEY = 'totalErrors' THEN RECORDING_VALUE END) AS TOTAL_ERRORS,
        MAX(CASE WHEN RECORDING_KEY = 'score' THEN RECORDING_VALUE END) AS GAME_SCORE
    FROM recording_{rgs_mode}             -- Key-value store of session metrics
    GROUP BY SESSION_ID                   -- Aggregate by session
) r ON sd.SESSION_ID = r.SESSION_ID       -- Join with session data

-- Filter for only the patients of interest (parameterized)
WHERE sd.PATIENT_ID IN :patient_ids

-- Sort result for easier analysis
ORDER BY sd.PATIENT_ID, sd.SESSION_DATE;

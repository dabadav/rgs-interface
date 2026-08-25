INSERT INTO prescription_staging (
    PRESCRIPTION_STAGING_ID, PATIENT_ID, PROTOCOL_ID, STARTING_DATE, ENDING_DATE, WEEKDAY,
    SESSION_DURATION, RECOMMENDATION_ID, WEEKS_SINCE_START, STATUS
) VALUES (
    NULL, :patient_id, :protocol_id, :starting_date, :ending_date, :weekday,
    :session_duration, :recommendation_id, :weeks_since_start, :status
);

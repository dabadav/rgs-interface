SELECT
    pe.SESSION_ID,
    pe.PATIENT_ID,
    pe.PROTOCOL_ID,
    pe.GAME_MODE,
    pe.SECONDS_FROM_START,
    pe.PARAMETER_KEY AS PE_KEY,
    CAST(pe.PARAMETER_VALUE AS FLOAT) AS PE_VALUE
FROM performance_estimators_{rgs_mode} pe
WHERE pe.PATIENT_ID IN :patient_ids;
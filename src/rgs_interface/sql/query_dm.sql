SELECT 
    dm.SESSION_ID,
    dm.PATIENT_ID,
    dm.PROTOCOL_ID,
    dm.GAME_MODE,
    dm.SECONDS_FROM_START,
    dm.PARAMETER_KEY AS DM_KEY,
    CAST(dm.PARAMETER_VALUE AS FLOAT) AS DM_VALUE
FROM difficulty_modulators_{rgs_mode} dm
WHERE dm.PATIENT_ID IN :patient_ids;

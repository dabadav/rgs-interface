-- Long-format scoring metrics written by ai-cdss per recommendation run.
SELECT
    RECOMMENDATION_ID,
    PROTOCOL_ID,
    METRIC_KEY,
    CAST(METRIC_VALUE AS DECIMAL(20,10)) AS METRIC_VALUE,
    METRIC_DATE
FROM recsys_metrics
WHERE PATIENT_ID = :patient_id
  AND (:recommendation_ids_any = 0 OR RECOMMENDATION_ID IN :recommendation_ids)
ORDER BY METRIC_DATE, PROTOCOL_ID, METRIC_KEY;

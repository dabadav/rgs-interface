INSERT INTO recsys_metrics (
    RECSYS_METRICS_ID, PATIENT_ID, PROTOCOL_ID, RECOMMENDATION_ID, METRIC_DATE, METRIC_KEY, METRIC_VALUE
) VALUES (
    NULL, :patient_id, :protocol_id, :recommendation_id, :metric_date, :metric_key, :metric_value
);

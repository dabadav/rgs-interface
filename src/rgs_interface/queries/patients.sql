-- patient table lookups. All filters optional.
SELECT *
FROM patient
WHERE (:patient_ids_any  = 0 OR PATIENT_ID  IN :patient_ids)
  AND (:hospital_ids_any = 0 OR HOSPITAL_ID IN :hospital_ids)
  AND (:name_like IS NULL OR PATIENT_USER LIKE :name_like)
ORDER BY PATIENT_ID;

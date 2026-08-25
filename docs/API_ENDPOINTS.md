# RGS DB API — endpoint contract (v1)

Compiled 2026-08-25 from every SQL statement issued by `cdss-supervisor@develop`
(dashboard, replay, backtest), `cdss-alert`, `ai-cdss` and `rgs_interface` itself.
31 distinct statements collapse into the 11 read endpoints below. Each entry is one
registry item in `rgs_interface.queries.registry` and one route in `rgs-db-api`.

Conventions

- Base path `/v1`. All routes `GET`, bearer auth, JSON envelope
  `{"rows": [...], "count": n}`; errors `{"error": str, "hint": str}` with 400/401/404/500.
- Column names are **verbatim** from today's SQL so client edits are mechanical.
- List params (`patient_ids`) are repeated query params, cap 500, bound with
  `bindparam(..., expanding=True)`.
- Dates serialise as ISO strings with no timezone shift (alert relies on `dateStrings: true`).
- `rgs_mode` ∈ {`plus`, `app`} selects `*_plus` / `*_app` tables where the SQL is templated.

---

## 1. `GET /v1/health`

Replaces `SELECT 1 AS ok` (supervisor `/healthz`). Also used by uptime checks.

Response: `{"status": "ok", "db": true}`.

---

## 2. `GET /v1/cohort`

The AISN cohort. Four near-identical queries exist today; this endpoint is the union of
their filters, all off by default so the default shape equals the supervisor's.

| param | type | default | effect |
|---|---|---|---|
| `patient_id` | int | — | single row (replay `SQL_COHORT_ROW`) |
| `arm` | str | — | `pad.aisn_group = :arm` (backtest uses `RGS+AI`) |
| `exclude_control` | bool | false | `pad.aisn_group <> 'Control'` (alert) |
| `active` | bool | false | `trial_start <= CURDATE() <= trial_end` (alert `HAVING trial_active = 1`) |
| `with_sessions` | bool | false | adds `last_session_at`, `days_without_session` (alert; costs a `session_plus` join) |

Columns: `patient_id`, `patient_name`, `hospital_name`, `trial_arm`, `trial_start`,
`trial_end`, `trial_active`, and with `with_sessions`: `last_session_at`, `days_without_session`.

> Supervisor today receives `name`, `aisn_group`, `patient_user`, `patient_id`,
> `start_date`, `end_date` and re-aliases them itself (`HOSPITAL_NAME`, `AISN_GROUP`,
> `PATIENT_USER`). The API adopts the alert's snake_case aliases as canonical; the
> supervisor's `fetch_cohort()` renames on the way in. This is the **one** place
> column names change — flagged in the cutover plan.

Canonical SQL:

```sql
SELECT
  pad.patient_id                              AS patient_id,
  p.patient_user                              AS patient_name,
  h.name                                      AS hospital_name,
  pad.aisn_group                              AS trial_arm,
  MIN(ct.start_date)                          AS trial_start,
  MAX(ct.end_date)                            AS trial_end,
  (MIN(ct.start_date) <= CURDATE() AND MAX(ct.end_date) >= CURDATE()) AS trial_active
  -- with_sessions adds:
  -- , MAX(s.STARTING_DATE)                        AS last_session_at
  -- , DATEDIFF(CURDATE(), MAX(s.STARTING_DATE))   AS days_without_session
FROM patient_aisn_data       AS pad
JOIN patient                 AS p   ON pad.patient_id   = p.patient_id
JOIN hospital                AS h   ON p.hospital_id    = h.hospital_id
JOIN clinical_trials         AS ct  ON pad.patient_id   = ct.patient_id
-- with_sessions adds:
-- LEFT JOIN prescription_plus  AS pp  ON pp.PATIENT_ID     = pad.patient_id
-- LEFT JOIN session_plus       AS s   ON s.PRESCRIPTION_ID = pp.PRESCRIPTION_ID AND s.STATUS = 'CLOSED'
WHERE h.name <> 'AISN Hospital test'
  AND p.patient_user LIKE 'AI%'
  AND p.patient_user NOT LIKE '%deleted%'
  AND (:patient_id IS NULL OR pad.patient_id = :patient_id)
  AND (:arm IS NULL OR pad.aisn_group = :arm)
  AND (NOT :exclude_control OR pad.aisn_group <> 'Control')
GROUP BY pad.patient_id, p.patient_user, h.name, pad.aisn_group
HAVING (NOT :active OR trial_active = 1)
ORDER BY pad.patient_id;
```

Replaces: alert `queries/cohort.sql`; supervisor `SQL_COHORT`; replay `SQL_COHORT_ROW`;
backtest `SQL_AISN_COHORT`.
Consumers: alert (`exclude_control=1&active=1&with_sessions=1`), supervisor, replay, backtest.

---

## 3. `GET /v1/protocols`

No params. Columns: `PROTOCOL_ID`, `PROTOCOL_NAME`, `PROTOCOL_TYPE_ID`, `PROTOCOL_TYPE_NAME`.

```sql
SELECT
    p.PROTOCOL_ID,
    p.NAME_KEY AS PROTOCOL_NAME,
    p.PROTOCOL_TYPE_ID,
    pt.PROTOCOL_TYPE AS PROTOCOL_TYPE_NAME
FROM protocol p
JOIN protocol_type pt ON p.PROTOCOL_TYPE_ID = pt.PROTOCOL_TYPE_ID
ORDER BY p.PROTOCOL_ID;
```

Replaces: supervisor `SQL_PROTOCOLS`. Consumers: supervisor. Cache candidate (static table).

---

## 4. `GET /v1/staging`

`prescription_staging` rows — CDSS proposals. Eight statements today differ only in
filters and column subsets; the endpoint returns the full column set and every filter
is optional.

| param | type | effect |
|---|---|---|
| `patient_ids` | int[] (required) | `PATIENT_ID IN :patient_ids` |
| `week` | int | `WEEKS_SINCE_START = :week` |
| `status` | str | `STATUS = :status` (alert uses `Pending`) |
| `recommendation_id` | str | `RECOMMENDATION_ID = :recommendation_id` |
| `week_start` | date | `DATE(STARTING_DATE) = :week_start` (ai_cdss `_already_prescribed`) |

Columns: `PRESCRIPTION_STAGING_ID`, `PATIENT_ID`, `PROTOCOL_ID`, `STARTING_DATE`,
`ENDING_DATE`, `WEEKDAY`, `SESSION_DURATION`, `RECOMMENDATION_ID`, `WEEKS_SINCE_START`, `STATUS`.

```sql
SELECT
    PRESCRIPTION_STAGING_ID,
    PATIENT_ID,
    PROTOCOL_ID,
    STARTING_DATE,
    ENDING_DATE,
    WEEKDAY,
    SESSION_DURATION,
    RECOMMENDATION_ID,
    WEEKS_SINCE_START,
    STATUS
FROM prescription_staging
WHERE PATIENT_ID IN :patient_ids
  AND (:week IS NULL OR WEEKS_SINCE_START = :week)
  AND (:status IS NULL OR STATUS = :status)
  AND (:recommendation_id IS NULL OR RECOMMENDATION_ID = :recommendation_id)
  AND (:week_start IS NULL OR DATE(STARTING_DATE) = :week_start)
ORDER BY PATIENT_ID, WEEKS_SINCE_START, RECOMMENDATION_ID, PROTOCOL_ID;
```

Replaces: alert `protocol_staging.sql`, `staging_pending.sql`; supervisor `SQL_STAGING`,
`SQL_STAGING_BULK`, inline week rows (`cur_df`), inline prev-week rows (`prev_df`);
replay `SQL_STAGING_WEEK`, `SQL_STAGING_PRIOR_WEEK_ACCEPTED`; ai_cdss `_already_prescribed`
(client counts rows).
Consumers: alert, supervisor, replay, ai_cdss.

---

## 5. `GET /v1/patients/{patient_id}/staging/latest`

Two small aggregates the dashboard runs before picking a week.

| param | type | effect |
|---|---|---|
| `week` | int | if given, also return the latest `RECOMMENDATION_ID` for that week |

Response: `{"max_week": int|null, "latest_recommendation_id": str|null}`.

```sql
-- max_week
SELECT MAX(WEEKS_SINCE_START) AS w
FROM prescription_staging
WHERE PATIENT_ID = :patient_id;

-- latest_recommendation_id (only when :week given)
SELECT RECOMMENDATION_ID, MAX(PRESCRIPTION_STAGING_ID) AS sid
FROM prescription_staging
WHERE PATIENT_ID = :patient_id AND WEEKS_SINCE_START = :week
GROUP BY RECOMMENDATION_ID
ORDER BY sid DESC
LIMIT 1;
```

Replaces: supervisor inline `latest` and `rid_df`. Consumers: supervisor.

---

## 6. `GET /v1/prescriptions`

`prescription_plus` rows — what clinicians actually prescribed.

| param | type | effect |
|---|---|---|
| `patient_ids` | int[] (required) | `PATIENT_ID IN :patient_ids` |
| `active_from`, `active_to` | datetime | window overlap: `STARTING_DATE < :active_to AND ENDING_DATE > :active_from` (backtest `SQL_PRIOR_PLUS`, supervisor weekly count) |
| `distinct_protocols` | bool | return only distinct `PATIENT_ID`, `PROTOCOL_ID` |
| `count` | bool | return `{"count": n}` instead of rows |

Columns: `PRESCRIPTION_ID`, `PATIENT_ID`, `PROTOCOL_ID`, `STARTING_DATE`, `ENDING_DATE`,
`WEEKDAY`, `SESSION_DURATION`.

```sql
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
```

Replaces: alert `protocol_prescriptions.sql`; supervisor `SQL_PRESCRIPTION`,
`SQL_PRESCRIPTION_BULK`, inline weekly `COUNT(*)`; backtest `SQL_PRIOR_PLUS`.
Consumers: alert, supervisor, backtest.

---

## 7. `GET /v1/patients/{patient_id}/adherence`

Per-prescription adherence rows (prescription × closed/aborted session × recorded duration).

Columns: `PRESCRIPTION_ID`, `PROTOCOL_ID`, `STARTING_DATE`, `WEEKDAY`, `PRESCRIBED_DURATION`,
`SESSION_ID`, `SESSION_DATE`, `SESSION_STATUS`, `RECORDED_DURATION`.

```sql
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
```

Replaces: supervisor `SQL_ADHERENCE`. Consumers: supervisor.

---

## 8. `GET /v1/sessions`

Session counts / rows per patient, optionally windowed. Today only the count is used.

| param | type | effect |
|---|---|---|
| `patient_id` | int (required) | via `prescription_plus.PATIENT_ID` |
| `status` | str | `s.STATUS = :status` (supervisor uses `CLOSED`) |
| `from`, `to` | datetime | `s.STARTING_DATE >= :from AND s.STARTING_DATE < :to` |
| `count` | bool | return `{"count": n}` |

Columns (when not `count`): `SESSION_ID`, `PRESCRIPTION_ID`, `PROTOCOL_ID`, `STARTING_DATE`,
`ENDING_DATE`, `STATUS`.

```sql
SELECT s.SESSION_ID, s.PRESCRIPTION_ID, p.PROTOCOL_ID, s.STARTING_DATE, s.ENDING_DATE, s.STATUS
FROM session_plus s
JOIN prescription_plus p ON s.PRESCRIPTION_ID = p.PRESCRIPTION_ID
WHERE p.PATIENT_ID = :patient_id
  AND (:status IS NULL OR s.STATUS = :status)
  AND (:from IS NULL OR s.STARTING_DATE >= :from)
  AND (:to   IS NULL OR s.STARTING_DATE <  :to)
ORDER BY s.STARTING_DATE;
```

Replaces: supervisor inline weekly closed-session `COUNT(*)`. Consumers: supervisor.

---

## 9. `GET /v1/recsys-metrics`

Long-format scoring metrics written by ai-cdss per recommendation run.

| param | type | effect |
|---|---|---|
| `patient_id` | int (required) | |
| `recommendation_ids` | str[] | `RECOMMENDATION_ID IN :recommendation_ids` |

Columns: `RECOMMENDATION_ID`, `PROTOCOL_ID`, `METRIC_KEY`, `METRIC_VALUE` (decimal),
`METRIC_DATE`.

```sql
SELECT
    RECOMMENDATION_ID,
    PROTOCOL_ID,
    METRIC_KEY,
    CAST(METRIC_VALUE AS DECIMAL(20,10)) AS METRIC_VALUE,
    METRIC_DATE
FROM recsys_metrics
WHERE PATIENT_ID = :patient_id
  AND (:recommendation_ids IS NULL OR RECOMMENDATION_ID IN :recommendation_ids)
ORDER BY METRIC_DATE, PROTOCOL_ID, METRIC_KEY;
```

Replaces: supervisor inline `metrics`; replay `SQL_HISTORICAL_METRICS`.
Consumers: supervisor, replay.

> Known prod issue: some rows carry `RECOMMENDATION_ID = 0` (UUID leak). Supervisor
> already skips metrics when rid is 0/None; API does not paper over it.

---

## 10. `GET /v1/clinical-trials`

Two uses: clinical scores per patient, and the **production CDSS trigger** query
(`fetch_patients_by_study`) — patients whose weekly recommendation is due today.

| param | type | effect |
|---|---|---|
| `patient_ids` | int[] | `PATIENT_ID IN :patient_ids` |
| `study_id` | int | `STUDY_ID = :study_id` |
| `due_today` | bool | `RECOMMEND = 1 AND CURDATE() <= END_DATE AND DATEDIFF(CURDATE(), START_DATE) % 7 = 0` |
| `with_scores` | bool | only rows with `CLINICAL_SCORES IS NOT NULL` |

Columns: `*` of `clinical_trials` (at least `PATIENT_ID`, `STUDY_ID`, `START_DATE`,
`END_DATE`, `RECOMMEND`, `CLINICAL_SCORES`). Fix exact column list in the row model
from `DESCRIBE clinical_trials` during Phase 1.

```sql
SELECT *
FROM clinical_trials
WHERE (:patient_ids IS NULL OR PATIENT_ID IN :patient_ids)
  AND (:study_id IS NULL OR STUDY_ID = :study_id)
  AND (NOT :due_today OR (
        RECOMMEND = 1
        AND CURDATE() <= END_DATE
        AND DATEDIFF(CURDATE(), START_DATE) % 7 = 0))
  AND (NOT :with_scores OR CLINICAL_SCORES IS NOT NULL);
```

Replaces: supervisor inline `CLINICAL_SCORES`; `rgs_interface.fetch_patients_by_study`
(ai_cdss `DBLoader`); `rgs_interface.fetch_clinical_data`.
Consumers: supervisor, ai_cdss.

---

## 11. `GET /v1/rgs-data`

Heavy per-session join used by ai-cdss feature building. Parquet by default when more
than one patient; JSON allowed for ≤ 1 patient.

| param | type | effect |
|---|---|---|
| `patient_ids` | int[] (required) | |
| `rgs_mode` | `plus`\|`app` | table suffix, default `plus` |
| `kind` | `full`\|`dm`\|`pe`\|`timeseries` | which `.sql`: `query.sql`, `query_dm.sql`, `query_pe.sql`, dm⋈pe |
| `format` | `json`\|`parquet` | default `parquet`; response `application/vnd.apache.parquet` |

`kind=full` columns: `PATIENT_ID`, `PRESCRIPTION_ID`, `SESSION_ID`, `PROTOCOL_ID`,
`PRESCRIPTION_STARTING_DATE`, `PRESCRIPTION_ENDING_DATE`, `SESSION_DATE`, `STATUS`,
`WEEKDAY_INDEX`, `REAL_SESSION_DURATION`, `PRESCRIBED_SESSION_DURATION`, `SESSION_DURATION`,
`ADHERENCE`, `DM_VALUE`.

`kind=dm` columns: `SESSION_ID`, `PATIENT_ID`, `PROTOCOL_ID`, `GAME_MODE`,
`SECONDS_FROM_START`, `DM_KEY`, `DM_VALUE`.

SQL: existing `rgs_interface/sql/query.sql`, `query_dm.sql`, `query_pe.sql` verbatim
(moved to `queries/rgs_data_full.sql`, `rgs_data_dm.sql`, `rgs_data_pe.sql`).

Replaces: `rgs_interface.fetch_rgs_data`, `fetch_dm_data`, `fetch_pe_data`,
`fetch_timeseries_data`. Consumers: ai_cdss via supervisor replay `--warmup`, ai-cdss prod.

---

## Not in v1

| statement | why |
|---|---|
| `add_prescription_staging_entry`, `add_recsys_metric_entry` | writes; ai-cdss prod keeps `SqlBackend` until `POST /v1/staging`, `POST /v1/recsys-metrics` exist |
| `fetch_patients`, `fetch_patients_by_hospital`, `fetch_patients_by_name` | no consumer; add `GET /v1/patients` if one appears |
| `query_emotional.sql`, `query_patient.sql` | no consumer |
| `query_old.sql`, `query__.sql`, `query_all.sql` | dead — delete |

## Table grants for the read-only API user

`patient`, `patient_aisn_data`, `hospital`, `clinical_trials`, `prescription_staging`,
`prescription_plus`, `session_plus`, `recording_plus`, `difficulty_modulators_plus`,
`performance_estimators_plus`, `recsys_metrics`, `protocol`, `protocol_type`
(+ `*_app` variants only if `rgs_mode=app` is kept).

## Source map

| source | statements |
|---|---|
| `cdss-supervisor/cdss-dashboard/app.py` | `SQL_COHORT`, `SQL_STAGING`, `SQL_PRESCRIPTION`, `SQL_ADHERENCE`, `SQL_PROTOCOLS`, `SQL_STAGING_BULK`, `SQL_PRESCRIPTION_BULK`, 9 inline `_fetch` |
| `cdss-supervisor/cdss-replay/replay_cdss.py` | `SQL_COHORT_ROW`, `SQL_STAGING_WEEK`, `SQL_STAGING_PRIOR_WEEK_ACCEPTED`, `SQL_HISTORICAL_METRICS` |
| `cdss-supervisor/cdss-backtest/backtest_aisn.py` | `SQL_AISN_COHORT`, `SQL_PRIOR_PLUS` |
| `cdss-alert/src/project/queries/` | `cohort`, `protocol_staging`, `protocol_prescriptions`, `staging_pending` |
| `rgs_interface/data/interface.py` | `fetch_rgs_data`, `fetch_dm_data`, `fetch_pe_data`, `fetch_timeseries_data`, `fetch_clinical_data`, `fetch_patients_by_study`, `fetch_patients*` |
| `ai_cdss/interface/recommender.py` | `_already_prescribed` |

## Consumer matrix

### cdss-alert (4 queries → 3 endpoints)

| today (`queries.json`) | endpoint | params |
|---|---|---|
| `cohort` | `GET /v1/cohort` | `exclude_control=1&active=1&with_sessions=1` |
| `protocol_staging` | `GET /v1/staging` | `patient_ids=…` |
| `staging_pending` | `GET /v1/staging` | `patient_ids=…&status=Pending` |
| `protocol_prescriptions` | `GET /v1/prescriptions` | `patient_ids=…` |

Handlers unchanged: `protocolViolation.js`, `pendingPrescriptions.js` and the declarative
`dropout_risk` alert read the same column names (`patient_id`, `trial_start`, `trial_arm`,
`PATIENT_ID`, `PROTOCOL_ID`, `WEEKDAY`, `WEEKS_SINCE_START`, `STARTING_DATE`, `STATUS`).

### cdss-supervisor dashboard (`app.py`, 16 statements → 9 endpoints)

| today | endpoint |
|---|---|
| `SQL_COHORT` / `fetch_cohort()` | `GET /v1/cohort` (rename columns on ingest: `hospital_name→name`, `trial_arm→aisn_group`, `patient_name→patient_user`, `trial_start→start_date`, `trial_end→end_date`) |
| `SQL_PROTOCOLS` / `fetch_protocols()` | `GET /v1/protocols` |
| `SQL_STAGING` / `fetch_staging(pid)` | `GET /v1/staging?patient_ids=pid` |
| `SQL_STAGING_BULK` | `GET /v1/staging?patient_ids=…` |
| inline `cur_df` (pid, week, rid) | `GET /v1/staging?patient_ids=pid&week=w&recommendation_id=rid` |
| inline `prev_df` (pid, week-1) | `GET /v1/staging?patient_ids=pid&week=w-1` |
| inline `MAX(WEEKS_SINCE_START)` + `rid_df` | `GET /v1/patients/{pid}/staging/latest?week=w` |
| `SQL_PRESCRIPTION` / `fetch_prescription(pid)` | `GET /v1/prescriptions?patient_ids=pid` |
| `SQL_PRESCRIPTION_BULK` | `GET /v1/prescriptions?patient_ids=…` |
| inline weekly `COUNT(*) prescription_plus` | `GET /v1/prescriptions?patient_ids=pid&active_from=…&active_to=…&count=1` |
| inline weekly `COUNT(*) session_plus CLOSED` | `GET /v1/sessions?patient_id=pid&status=CLOSED&from=…&to=…&count=1` |
| `SQL_ADHERENCE` / `fetch_adherence(pid)` | `GET /v1/patients/{pid}/adherence` |
| inline `recsys_metrics` (pid, rid) | `GET /v1/recsys-metrics?patient_id=pid&recommendation_ids=rid` |
| inline `CLINICAL_SCORES` | `GET /v1/clinical-trials?patient_ids=…&with_scores=1` |
| `SELECT 1` `/healthz` | `GET /v1/health` |

### cdss-supervisor replay + backtest (6 statements → 4 endpoints)

| today | endpoint |
|---|---|
| `SQL_COHORT_ROW` | `GET /v1/cohort?patient_id=pid` |
| `SQL_STAGING_WEEK` | `GET /v1/staging?patient_ids=pid&week=w` |
| `SQL_STAGING_PRIOR_WEEK_ACCEPTED` | `GET /v1/staging?patient_ids=pid&week=w-1` (client does `DISTINCT PROTOCOL_ID, RECOMMENDATION_ID, STATUS`) |
| `SQL_HISTORICAL_METRICS` | `GET /v1/recsys-metrics?patient_id=pid&recommendation_ids=…` |
| `SQL_AISN_COHORT` | `GET /v1/cohort?arm=RGS%2BAI` |
| `SQL_PRIOR_PLUS` | `GET /v1/prescriptions?patient_ids=pid&active_from=…&active_to=…&distinct_protocols=1` |

### ai-cdss via replay `--warmup` (4 → 3 endpoints)

| today (`rgs_interface`) | endpoint |
|---|---|
| `fetch_rgs_data` | `GET /v1/rgs-data?kind=full&rgs_mode=plus&format=parquet` |
| `fetch_dm_data` | `GET /v1/rgs-data?kind=dm` |
| `fetch_patients_by_study` | `GET /v1/clinical-trials?study_id=…&due_today=1` |
| `_already_prescribed` | `GET /v1/staging?patient_ids=pid&week_start=YYYY-MM-DD&count=1` |

# rgs_interface v1 — the shared DB contract

Status: **plan** (branch `feat/api-contract`, 2026-08-25). Nothing below is implemented yet.

## Why

The new DB host blocks 3306 externally. Sysadmin decision: a typed HTTP API sits in front
of the database; `cdss-supervisor`, `cdss-alert` and (later) `ai-cdss` consume it.

Rather than a separate API codebase that re-implements every query, `rgs_interface`
becomes the contract: row models + a named query registry + two backends. The API server
is a generic router over the registry; Python clients call the same repository methods
against an HTTP backend. Parity is structural.

Endpoint list and SQL: [`API_ENDPOINTS.md`](API_ENDPOINTS.md).

## Target layout

```
src/rgs_interface/
├── __init__.py
├── models.py              pydantic row models — CohortRow, ProtocolRow, StagingRow,
│                          StagingLatest, PrescriptionRow, AdherenceRow, SessionRow,
│                          RecsysMetricRow, ClinicalTrialRow, RgsDataRow, DmRow, PeRow
├── params.py              pydantic param models, one per endpoint (CohortParams, StagingParams, …)
├── queries/
│   ├── __init__.py
│   ├── registry.py        QUERIES: dict[str, Query]  — Query(name, sql_file, params, row, route)
│   ├── cohort.sql
│   ├── protocols.sql
│   ├── staging.sql
│   ├── staging_max_week.sql
│   ├── staging_latest_rid.sql
│   ├── prescriptions.sql
│   ├── adherence.sql
│   ├── sessions.sql
│   ├── recsys_metrics.sql
│   ├── clinical_trials.sql
│   ├── rgs_data_full.sql   (was sql/query.sql)
│   ├── rgs_data_dm.sql     (was sql/query_dm.sql)
│   └── rgs_data_pe.sql     (was sql/query_pe.sql)
├── backends/
│   ├── __init__.py
│   ├── base.py            class Backend(Protocol): fetch(query: Query, params: BaseModel) -> DataFrame
│   ├── sql.py             SqlBackend(engine) — bindparam expanding, {rgs_mode} templating, READ ONLY session
│   └── http.py            HttpBackend(base_url, token) — requests, parquet decode, retry 502/503
├── repository.py          class RgsRepository:
│                            def __init__(self, backend: Backend)
│                            cohort(...), protocols(), staging(...), staging_latest(...),
│                            prescriptions(...), adherence(pid), sessions(...),
│                            recsys_metrics(...), clinical_trials(...), rgs_data(...)
│                            # compat names ai_cdss calls today:
│                            fetch_rgs_data(patient_ids, rgs_mode), fetch_dm_data(...),
│                            fetch_patients_by_study(study_ids)
│                            # writes — SqlBackend only, HttpBackend raises NotImplementedError:
│                            add_prescription_staging_entry(row), add_recsys_metric_entry(row)
├── data/
│   ├── interface.py       DatabaseInterface(RgsRepository): __init__ builds SqlBackend(get_db_engine());
│   │                      emits DeprecationWarning; `_fetch` kept but private-by-convention
│   ├── schemas.py         unchanged (PrescriptionStagingRow, RecsysMetricsRow dataclasses)
│   └── preprocess.py      → moved to analysis/ (extra)
├── analysis/              preprocess.py (+ anything importing seaborn / sklearn)
├── db.py                  unchanged (engine factory)
├── config.py              unchanged
└── cli.py                 unchanged
```

`Query.route` carries the HTTP shape (`"/cohort"`, `"/patients/{patient_id}/adherence"`) so
`rgs-db-api` can do:

```python
for q in QUERIES.values():
    app.add_api_route(f"/v1{q.route}", make_handler(q), methods=["GET"], response_model=Envelope[q.row])
```

## pyproject extras

```toml
[project]
dependencies = ["pandas[parquet]>=2.2,<3", "pydantic>=2.7,<3", "pyyaml", "python-dotenv"]

[project.optional-dependencies]
sql      = ["sqlalchemy>=2.0,<3", "pymysql>=1.1,<2"]
http     = ["requests>=2.32,<3", "pyarrow>=16"]
analysis = ["numpy<2", "seaborn", "matplotlib", "scikit-learn"]
cli      = ["typer"]
```

- `rgs-db-api` installs `rgs-interface[sql]`.
- `cdss-supervisor` installs `rgs-interface[http]`.
- `ai-cdss` prod installs `rgs-interface[sql]` (still writes) — moves to `[http]` when POST routes exist.
- Anything importing `preprocess` installs `[analysis]`.

## Migration steps (this repo)

1. `models.py`, `params.py` — write from `API_ENDPOINTS.md`; column names verbatim.
2. `queries/*.sql` + `registry.py` — move SQL in; delete `sql/query_old.sql`, `query__.sql`,
   `query_all.sql`; keep `query_emotional.sql`, `query_patient.sql` unregistered until a consumer appears.
3. `backends/sql.py` — lift `_fetch` body: `.sql` loading, `{rgs_mode}` format, `text()`,
   `pd.read_sql`. Add `bindparam(expanding=True)` for list params (today relies on tuple
   rendering). Add `SET SESSION TRANSACTION READ ONLY` on connect for non-write repositories.
4. `repository.py` — typed methods; compat aliases for ai_cdss.
5. `data/interface.py` — subclass shim, DeprecationWarning, existing tests stay green.
6. `backends/http.py` — mirror of sql backend against `/v1{route}`; parquet when
   `Accept: application/vnd.apache.parquet`.
7. Tests: `tests/test_registry.py` runs every registry entry against a MariaDB fixture
   (5 cohort patients) and asserts `set(df.columns) == set(row.model_fields)`.
   `tests/test_http_backend.py` uses `responses`/`respx` to mock the API.
8. Bump `pyproject` to `1.0.0`, tag `v1.0.0`. CHANGELOG: breaking = extras split,
   `DatabaseInterface` deprecated.

## Versioning

- API path `/v1` ⇔ `rgs_interface` major version 1. A breaking change to any row model
  bumps both.
- Server and clients pin the same tag (`_RGS_INTERFACE_REF` in supervisor's `cloudbuild.yaml`).
- `openapi.json` is generated by the server from the pydantic models; `cdss-alert` runs
  `openapi-typescript` on it at build time.

## Open decisions (need answers before step 3)

| question | default if unanswered |
|---|---|
| Keep `rgs_mode=app` tables? | yes, templated as today |
| Cohort column naming: alert snake_case vs supervisor raw | snake_case (alert) is canonical; supervisor renames |
| `clinical_trials` exact column list for `ClinicalTrialRow` | `SELECT *` until `DESCRIBE` is run on the new host |
| Writes over HTTP | out of v1; `HttpBackend` raises |
| Auth header format | `Authorization: Bearer <token>`, one token per consumer |

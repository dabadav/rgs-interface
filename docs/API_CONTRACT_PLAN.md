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

## Change list with sketches

### 1. `models.py` — new

One pydantic model per endpoint response row. Field names verbatim from SQL.

```python
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel

class CohortRow(BaseModel):
    patient_id: int
    patient_name: str
    hospital_name: str
    trial_arm: str
    trial_start: date
    trial_end: date
    trial_active: bool
    last_session_at: datetime | None = None      # only with with_sessions=1
    days_without_session: int | None = None

class ProtocolRow(BaseModel):
    PROTOCOL_ID: int
    PROTOCOL_NAME: str
    PROTOCOL_TYPE_ID: int
    PROTOCOL_TYPE_NAME: str

class StagingRow(BaseModel):
    PRESCRIPTION_STAGING_ID: int
    PATIENT_ID: int
    PROTOCOL_ID: int
    STARTING_DATE: datetime
    ENDING_DATE: datetime
    WEEKDAY: str
    SESSION_DURATION: int
    RECOMMENDATION_ID: str | None
    WEEKS_SINCE_START: int
    STATUS: str

class StagingLatest(BaseModel):
    max_week: int | None
    latest_recommendation_id: str | None

class PrescriptionRow(BaseModel):
    PRESCRIPTION_ID: int
    PATIENT_ID: int
    PROTOCOL_ID: int
    STARTING_DATE: datetime
    ENDING_DATE: datetime
    WEEKDAY: str
    SESSION_DURATION: int

class AdherenceRow(BaseModel):
    PRESCRIPTION_ID: int
    PROTOCOL_ID: int
    STARTING_DATE: datetime
    WEEKDAY: str
    PRESCRIBED_DURATION: int
    SESSION_ID: int | None
    SESSION_DATE: datetime | None
    SESSION_STATUS: str | None
    RECORDED_DURATION: float | None

class SessionRow(BaseModel):
    SESSION_ID: int
    PRESCRIPTION_ID: int
    PROTOCOL_ID: int
    STARTING_DATE: datetime
    ENDING_DATE: datetime | None
    STATUS: str

class RecsysMetricRow(BaseModel):
    RECOMMENDATION_ID: str
    PROTOCOL_ID: int
    METRIC_KEY: str
    METRIC_VALUE: Decimal
    METRIC_DATE: datetime

class ClinicalTrialRow(BaseModel):
    model_config = {"extra": "allow"}            # SELECT * until DESCRIBE on new host
    PATIENT_ID: int
    STUDY_ID: int
    START_DATE: date
    END_DATE: date
    RECOMMEND: int
    CLINICAL_SCORES: str | None

class RgsDataRow(BaseModel):
    PATIENT_ID: int
    PRESCRIPTION_ID: int
    SESSION_ID: int | None
    PROTOCOL_ID: int
    PRESCRIPTION_STARTING_DATE: datetime
    PRESCRIPTION_ENDING_DATE: datetime
    SESSION_DATE: datetime | None
    STATUS: str | None
    WEEKDAY_INDEX: int | None
    REAL_SESSION_DURATION: int | None
    PRESCRIBED_SESSION_DURATION: int
    SESSION_DURATION: int | None
    ADHERENCE: float | None
    DM_VALUE: float | None

class DmRow(BaseModel):
    SESSION_ID: int
    PATIENT_ID: int
    PROTOCOL_ID: int
    GAME_MODE: str
    SECONDS_FROM_START: int
    DM_KEY: str
    DM_VALUE: float
```

Types are best guesses from usage; step 7's registry test corrects them against real rows.

### 2. `params.py` — new

One pydantic model per endpoint's query parameters. Doubles as FastAPI `Depends()` and
as the validated dict handed to SQL.

```python
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field, conlist

PatientIds = conlist(int, min_length=1, max_length=500)

class NoParams(BaseModel): ...

class CohortParams(BaseModel):
    patient_id: int | None = None
    arm: str | None = None
    exclude_control: bool = False
    active: bool = False
    with_sessions: bool = False

class StagingParams(BaseModel):
    patient_ids: PatientIds
    week: int | None = None
    status: str | None = None
    recommendation_id: str | None = None
    week_start: date | None = None
    count: bool = False

class StagingLatestParams(BaseModel):
    patient_id: int                       # path param
    week: int | None = None

class PrescriptionParams(BaseModel):
    patient_ids: PatientIds
    active_from: datetime | None = None
    active_to: datetime | None = None
    distinct_protocols: bool = False
    count: bool = False

class PatientParams(BaseModel):
    patient_id: int                       # path param (adherence)

class SessionParams(BaseModel):
    patient_id: int
    status: str | None = None
    from_: datetime | None = Field(None, alias="from")
    to: datetime | None = None
    count: bool = False

class RecsysMetricParams(BaseModel):
    patient_id: int
    recommendation_ids: list[str] | None = None

class ClinicalTrialParams(BaseModel):
    patient_ids: PatientIds | None = None
    study_id: int | None = None
    due_today: bool = False
    with_scores: bool = False

class RgsDataParams(BaseModel):
    patient_ids: PatientIds
    rgs_mode: Literal["plus", "app"] = "plus"
    kind: Literal["full", "dm", "pe", "timeseries"] = "full"
    format: Literal["json", "parquet"] = "parquet"
```

### 3. `queries/registry.py` — new

```python
from dataclasses import dataclass
from importlib.resources import files
from pydantic import BaseModel
from rgs_interface import models as M, params as P

@dataclass(frozen=True)
class Query:
    name: str
    route: str                     # HTTP path under /v1, may contain {path_params}
    params: type[BaseModel]
    row: type[BaseModel]
    sql: str | dict[str, str]      # file name, or {kind: file} for rgs_data
    templated: bool = False        # True → format(rgs_mode=...)
    multi: bool = False            # True → several statements (staging_latest)

    def sql_text(self, kind: str | None = None) -> str:
        f = self.sql if isinstance(self.sql, str) else self.sql[kind]
        return (files("rgs_interface.queries") / f).read_text()

QUERIES: dict[str, Query] = {
    "cohort":          Query("cohort", "/cohort", P.CohortParams, M.CohortRow, "cohort.sql"),
    "protocols":       Query("protocols", "/protocols", P.NoParams, M.ProtocolRow, "protocols.sql"),
    "staging":         Query("staging", "/staging", P.StagingParams, M.StagingRow, "staging.sql"),
    "staging_latest":  Query("staging_latest", "/patients/{patient_id}/staging/latest",
                             P.StagingLatestParams, M.StagingLatest,
                             {"max_week": "staging_max_week.sql", "latest_rid": "staging_latest_rid.sql"}, multi=True),
    "prescriptions":   Query("prescriptions", "/prescriptions", P.PrescriptionParams, M.PrescriptionRow, "prescriptions.sql"),
    "adherence":       Query("adherence", "/patients/{patient_id}/adherence", P.PatientParams, M.AdherenceRow, "adherence.sql"),
    "sessions":        Query("sessions", "/sessions", P.SessionParams, M.SessionRow, "sessions.sql"),
    "recsys_metrics":  Query("recsys_metrics", "/recsys-metrics", P.RecsysMetricParams, M.RecsysMetricRow, "recsys_metrics.sql"),
    "clinical_trials": Query("clinical_trials", "/clinical-trials", P.ClinicalTrialParams, M.ClinicalTrialRow, "clinical_trials.sql"),
    "rgs_data":        Query("rgs_data", "/rgs-data", P.RgsDataParams, M.RgsDataRow,
                             {"full": "rgs_data_full.sql", "dm": "rgs_data_dm.sql", "pe": "rgs_data_pe.sql"}, templated=True),
}
```

`health` is not a registry entry — the server implements it directly.

### 4. `queries/*.sql` — moved / new

| file | from |
|---|---|
| `cohort.sql` | new canonical (API_ENDPOINTS §2) |
| `protocols.sql` | supervisor `SQL_PROTOCOLS` |
| `staging.sql` | new canonical (§4) |
| `staging_max_week.sql`, `staging_latest_rid.sql` | supervisor inline |
| `prescriptions.sql` | new canonical (§6) |
| `adherence.sql` | supervisor `SQL_ADHERENCE` |
| `sessions.sql` | new (§8) |
| `recsys_metrics.sql` | replay `SQL_HISTORICAL_METRICS` + optional filter |
| `clinical_trials.sql` | new (§10), absorbs `fetch_patients_by_study` |
| `rgs_data_full.sql` | `sql/query.sql` verbatim |
| `rgs_data_dm.sql` | `sql/query_dm.sql` verbatim |
| `rgs_data_pe.sql` | `sql/query_pe.sql` verbatim |
| **deleted** | `sql/query_old.sql`, `sql/query__.sql`, `sql/query_all.sql` |
| **kept, unregistered** | `sql/query_emotional.sql`, `sql/query_patient.sql` (move to `queries/_unused/`) |

Optional filters use the `(:p IS NULL OR col = :p)` idiom so one statement serves every
variant. MySQL/MariaDB plan quality is fine at these row counts; revisit if `/staging`
on 500 patients gets slow.

### 5. `backends/base.py`, `backends/sql.py` — new (lifted from `_fetch`)

```python
# base.py
from typing import Protocol
import pandas as pd
from pydantic import BaseModel
from rgs_interface.queries.registry import Query

class Backend(Protocol):
    def fetch(self, q: Query, params: BaseModel, *, kind: str | None = None) -> pd.DataFrame: ...
```

```python
# sql.py
import pandas as pd
from sqlalchemy import text, bindparam, event
from sqlalchemy.engine import Engine

class SqlBackend:
    def __init__(self, engine: Engine, read_only: bool = True):
        self.engine = engine
        if read_only:
            @event.listens_for(engine, "connect")
            def _ro(dbapi_conn, _):
                dbapi_conn.cursor().execute("SET SESSION TRANSACTION READ ONLY")

    def fetch(self, q, params, *, kind=None):
        sql = q.sql_text(kind)
        p = params.model_dump(by_alias=True)
        if q.templated:
            sql = sql.format(rgs_mode=p.pop("rgs_mode"))
        stmt = text(sql)
        for k, v in p.items():
            if isinstance(v, (list, tuple)):
                stmt = stmt.bindparams(bindparam(k, expanding=True))
        with self.engine.connect() as conn:
            return pd.read_sql(stmt, conn, params=p, dtype_backend="numpy_nullable")
```

`_fetch`'s `.sql`-name-vs-raw-string branching, `output_file` CSV side effect, and the
`format(rgs_mode=...)` on raw strings all go away. `output_file` becomes the caller's job.

### 6. `backends/http.py` — new

```python
import io, requests, pandas as pd

class HttpBackend:
    def __init__(self, base_url: str, token: str, timeout: float = 120):
        self.base, self.timeout = base_url.rstrip("/"), timeout
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {token}"
        # retry 502/503/504, backoff, via urllib3 Retry on the adapter

    def fetch(self, q, params, *, kind=None):
        p = params.model_dump(by_alias=True, exclude_none=True)
        route = q.route.format(**{k: p.pop(k) for k in _path_keys(q.route)})
        if kind: p["kind"] = kind
        want_parquet = p.get("format") == "parquet"
        r = self.s.get(f"{self.base}/v1{route}", params=p, timeout=self.timeout,
                       headers={"Accept": "application/vnd.apache.parquet" if want_parquet else "application/json"})
        r.raise_for_status()
        if want_parquet:
            return pd.read_parquet(io.BytesIO(r.content))
        body = r.json()
        return pd.DataFrame(body["rows"], columns=list(q.row.model_fields))
```

Lists serialise as repeated params (`patient_ids=1&patient_ids=2`) — `requests` does that
for list values by default.

### 7. `repository.py` — new

```python
class RgsRepository:
    def __init__(self, backend: Backend):
        self.b = backend

    def cohort(self, **kw) -> pd.DataFrame:
        return self.b.fetch(QUERIES["cohort"], CohortParams(**kw))
    def protocols(self): ...
    def staging(self, patient_ids, **kw): ...
    def staging_latest(self, patient_id, week=None) -> StagingLatest: ...
    def prescriptions(self, patient_ids, **kw): ...
    def adherence(self, patient_id): ...
    def sessions(self, patient_id, **kw): ...
    def recsys_metrics(self, patient_id, recommendation_ids=None): ...
    def clinical_trials(self, **kw): ...
    def rgs_data(self, patient_ids, rgs_mode="plus", kind="full"): ...

    # --- compat: names ai_cdss DBLoader calls today ---
    def fetch_rgs_data(self, patient_ids, rgs_mode="plus", output_file=None):
        df = self.rgs_data(patient_ids, rgs_mode, "full")
        if output_file: df.to_csv(output_file, index=False)
        return df
    def fetch_dm_data(self, patient_ids, rgs_mode="plus", output_file=None): ...
    def fetch_pe_data(...): ...
    def fetch_timeseries_data(...): ...        # dm ⋈ pe as today
    def fetch_patients_by_study(self, study_ids):
        return self.clinical_trials(study_id=study_ids[0], due_today=True)   # today's SQL binds a 1-tuple

    # --- writes: SqlBackend only ---
    def add_prescription_staging_entry(self, entry): 
        if not isinstance(self.b, SqlBackend): raise NotImplementedError("writes need SqlBackend until POST /v1/staging exists")
        ...  # body moves here unchanged from data/interface.py
    def add_recsys_metric_entry(self, entry): ...
```

### 8. `data/interface.py` — shrinks to a shim

```python
import warnings
from rgs_interface.backends.sql import SqlBackend
from rgs_interface.db import get_db_engine
from rgs_interface.repository import RgsRepository

class DatabaseInterface(RgsRepository):
    def __init__(self):
        warnings.warn("DatabaseInterface is deprecated; use RgsRepository(SqlBackend(...))", DeprecationWarning, stacklevel=2)
        engine = get_db_engine()
        self.engine = engine                       # ai_cdss checks `engine is None`
        super().__init__(SqlBackend(engine, read_only=False))   # ai_cdss prod still writes

    def _fetch(self, query, params=None, rgs_mode=None, output_file=None, dtype_backend="numpy_nullable"):
        # kept for one minor version so supervisor@develop keeps running during migration; raw SQL passthrough
        ...
```

`fetch_patients`, `fetch_patients_by_hospital`, `fetch_patients_by_name`, `fetch_clinical_data`
stay on the shim only (raw SQL) — no consumers, not promoted to the registry.

### 9. `analysis/` — move

`data/preprocess.py` → `analysis/preprocess.py`; `data/__init__.py` stops importing it.
This is what lets core install without numpy<2 / seaborn / sklearn.

### 10. `pyproject.toml`

- version `1.0.0`
- deps + extras as in "pyproject extras" above
- `[tool.poetry]` → keep poetry-core build backend, or switch to hatchling; either is fine

### 11. Tests

```
tests/
├── conftest.py              MariaDB fixture (testcontainers) + schema + 5-patient seed
├── test_registry.py         for q in QUERIES: SqlBackend.fetch(q, default_params) → columns ⊇ row fields
├── test_repository.py       compat method names still exist and return DataFrames
├── test_http_backend.py     respx-mocked API; path params, list params, parquet decode
└── test_interface_shim.py   DatabaseInterface() warns, still works
```

### Diff footprint

| | files | approx lines |
|---|---|---|
| new | `models.py`, `params.py`, `queries/registry.py`, `backends/*.py`, `repository.py`, 10 `.sql`, 4 tests | ~900 |
| moved | 3 `.sql`, `preprocess.py` | 0 |
| shrunk | `data/interface.py` (≈300 → ≈80) | −220 |
| deleted | 3 dead `.sql` | −400 |

# rgs_interface v1 — minimal DB contract + API

Status: **plan** (branch `feat/api-contract`, 2026-08-25). Nothing below is implemented yet.

## Why

The new DB host blocks 3306 externally. Sysadmin decision: a typed HTTP API sits in front
of the database; `cdss-supervisor`, `cdss-alert` and (later) `ai-cdss` consume it.

`rgs_interface` becomes that contract *and* that server. Design rule for this package:
**every module must answer "what breaks if this doesn't exist"**. Anything that only adds
ergonomics is out.

Endpoint list and SQL: [`API_ENDPOINTS.md`](API_ENDPOINTS.md).

## Design

Three ideas, nothing else:

1. **Registry** — `name → (param model, row model)`; SQL lives in `queries/<name>.sql`.
   The row model is the contract: field names are the columns, field types are validated
   on every server response.
2. **Two backends with one method** — `SqlBackend.fetch(name, **params)` runs the SQL;
   `HttpBackend.fetch(name, **params)` calls `GET /v1/<name>`; both return a DataFrame.
3. **Server is a loop** — for each registry entry, mount `GET /v1/<name>`, validate params
   with the param model, run `SqlBackend.fetch`, **validate rows with the row model**,
   return parquet (Python clients) or JSON (JS clients) by `Accept` header.

Parity is structural: server and client import the same registry from the same package
version. Validation happens once, at the source; clients trust the server.

## Layout

```
src/rgs_interface/
├── __init__.py        from .sql import SqlBackend ; from .http import HttpBackend
├── models.py          12 pydantic row models (the contract)                     ~150 lines
├── registry.py        Query dataclass, 11 param models, QUERIES dict           ~130
├── queries/
│   ├── cohort.sql  protocols.sql  staging.sql  staging_latest.sql
│   ├── prescriptions.sql  adherence.sql  sessions.sql  recsys_metrics.sql
│   ├── clinical_trials.sql
│   ├── rgs_data.sql   (was sql/query.sql)
│   ├── dm_data.sql    (was sql/query_dm.sql)
│   └── pe_data.sql    (was sql/query_pe.sql)
├── sql.py             SqlBackend: fetch + add_prescription_staging_entry + add_recsys_metric_entry   ~90
├── http.py            HttpBackend: fetch                                                             ~40
├── server.py          FastAPI app, validates rows before responding (extra: [server])                ~90
├── db.py              engine factory                          (existing, unchanged)
├── config.py          credentials                             (existing, unchanged)
├── schemas.py         PrescriptionStagingRow, RecsysMetricsRow (existing, moved up from data/)
└── cli.py             set-credentials, check-credentials, fetch <name>   (existing, shrunk)

Dockerfile             python:3.12-slim, pip install ".[sql,server]", uvicorn rgs_interface.server:app
docker-compose.yml     network_mode: host, env_file .env
tests/
├── conftest.py        MariaDB via testcontainers, schema + 5-patient seed, FastAPI TestClient
└── test_contract.py   for name in QUERIES: sql == http, every row validates against q.row
```

Deleted: `data/interface.py`, `data/preprocess.py`, `data/__init__.py`, `sql/query_old.sql`,
`sql/query__.sql`, `sql/query_all.sql`, `sql/query_emotional.sql`, `sql/query_patient.sql`.

## Dependencies

```toml
[project]
requires-python = ">=3.12"
dependencies = ["pandas[parquet]>=2.2,<3", "pydantic>=2.7,<3", "pyyaml", "python-dotenv"]

[project.optional-dependencies]
sql    = ["sqlalchemy>=2.0,<3", "pymysql>=1.1,<2"]
http   = ["requests>=2.32,<3"]
server = ["rgs-interface[sql]", "fastapi>=0.115", "uvicorn[standard]>=0.30"]
cli    = ["typer>=0.12"]
```

| project | installs | uses |
|---|---|---|
| API server (DB host) | `rgs-interface[server]` | `uvicorn rgs_interface.server:app` |
| cdss-supervisor | `rgs-interface[http]` | `HttpBackend(url, token)` |
| ai-cdss prod (today) | `rgs-interface@v0.4.1` — frozen | unchanged |
| ai-cdss when it upgrades | `rgs-interface[sql]` (still writes) | `SqlBackend(engine)`; 3 fetch calls + 2 writes renamed |
| cdss-alert (JS) | nothing | `fetch()` with `Accept: application/json` |

## Code

### `models.py`

One pydantic model per query result row. Field names are the SQL column names verbatim;
types are what the DB must deliver. `extra="forbid"` so an unexpected column fails loudly.

```python
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class Row(BaseModel):
    model_config = ConfigDict(extra="forbid")

class CohortRow(Row):
    patient_id: int
    patient_name: str
    hospital_name: str
    trial_arm: str
    trial_start: date
    trial_end: date
    trial_active: bool
    last_session_at: datetime | None
    days_without_session: int | None

class ProtocolRow(Row):
    PROTOCOL_ID: int
    PROTOCOL_NAME: str
    PROTOCOL_TYPE_ID: int
    PROTOCOL_TYPE_NAME: str

class StagingRow(Row):
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

class StagingLatest(Row):
    max_week: int | None
    latest_recommendation_id: str | None

class PrescriptionRow(Row):
    PRESCRIPTION_ID: int
    PATIENT_ID: int
    PROTOCOL_ID: int
    STARTING_DATE: datetime
    ENDING_DATE: datetime
    WEEKDAY: str
    SESSION_DURATION: int

class AdherenceRow(Row):
    PRESCRIPTION_ID: int
    PROTOCOL_ID: int
    STARTING_DATE: datetime
    WEEKDAY: str
    PRESCRIBED_DURATION: int
    SESSION_ID: int | None
    SESSION_DATE: datetime | None
    SESSION_STATUS: str | None
    RECORDED_DURATION: float | None

class SessionRow(Row):
    SESSION_ID: int
    PRESCRIPTION_ID: int
    PROTOCOL_ID: int
    STARTING_DATE: datetime
    ENDING_DATE: datetime | None
    STATUS: str

class RecsysMetricRow(Row):
    RECOMMENDATION_ID: str
    PROTOCOL_ID: int
    METRIC_KEY: str
    METRIC_VALUE: Decimal
    METRIC_DATE: datetime

class ClinicalTrialRow(Row):
    model_config = ConfigDict(extra="allow")   # SELECT * until DESCRIBE on the new host
    PATIENT_ID: int
    STUDY_ID: int
    START_DATE: date
    END_DATE: date
    RECOMMEND: int
    CLINICAL_SCORES: str | None

class RgsDataRow(Row):
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

class DmRow(Row):
    SESSION_ID: int
    PATIENT_ID: int
    PROTOCOL_ID: int
    GAME_MODE: str
    SECONDS_FROM_START: int
    DM_KEY: str
    DM_VALUE: float

class PeRow(Row):
    model_config = ConfigDict(extra="allow")   # from query_pe.sql at implementation time
    SESSION_ID: int
    PATIENT_ID: int
    PROTOCOL_ID: int
```

Types are best guesses from today's usage; the parity test corrects them against real rows
before `v1.0.0` is tagged.

### `registry.py`

```python
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, conlist
from rgs_interface import models as M

PatientIds = conlist(int, min_length=1, max_length=500)

class NoParams(BaseModel): ...
class CohortParams(BaseModel):
    patient_id: int | None = None
    arm: str | None = None
    exclude_control: bool = False
    active: bool = False
class StagingParams(BaseModel):
    patient_ids: PatientIds
    week: int | None = None
    status: str | None = None
    recommendation_id: str | None = None
    week_start: date | None = None
class StagingLatestParams(BaseModel):
    patient_id: int
    week: int | None = None
class PrescriptionParams(BaseModel):
    patient_ids: PatientIds
    active_from: datetime | None = None
    active_to: datetime | None = None
class PatientParams(BaseModel):
    patient_id: int
class SessionParams(BaseModel):
    patient_id: int
    status: str | None = None
    since: datetime | None = None
    until: datetime | None = None
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

@dataclass(frozen=True)
class Query:
    params: type[BaseModel]
    row: type[BaseModel]

    @property
    def columns(self) -> tuple[str, ...]:
        return tuple(self.row.model_fields)

QUERIES: dict[str, Query] = {
    "cohort":          Query(CohortParams,        M.CohortRow),
    "protocols":       Query(NoParams,            M.ProtocolRow),
    "staging":         Query(StagingParams,       M.StagingRow),
    "staging_latest":  Query(StagingLatestParams, M.StagingLatest),
    "prescriptions":   Query(PrescriptionParams,  M.PrescriptionRow),
    "adherence":       Query(PatientParams,       M.AdherenceRow),
    "sessions":        Query(SessionParams,       M.SessionRow),
    "recsys_metrics":  Query(RecsysMetricParams,  M.RecsysMetricRow),
    "clinical_trials": Query(ClinicalTrialParams, M.ClinicalTrialRow),
    "rgs_data":        Query(RgsDataParams,       M.RgsDataRow),
    "dm_data":         Query(RgsDataParams,       M.DmRow),
    "pe_data":         Query(RgsDataParams,       M.PeRow),
}

def sql_text(name: str) -> str:
    from importlib.resources import files
    return (files("rgs_interface.queries") / f"{name}.sql").read_text()
```

Rule: a param named `rgs_mode` is substituted into the SQL text (`{rgs_mode}`), everything
else is a bind parameter. Optional filters use `(:p IS NULL OR col = :p)` in the SQL.

### `sql.py`

```python
import pandas as pd
from sqlalchemy import text, bindparam, event
from sqlalchemy.engine import Engine
from rgs_interface.registry import QUERIES, sql_text
from rgs_interface.schemas import PrescriptionStagingRow, RecsysMetricsRow

class SqlBackend:
    def __init__(self, engine: Engine, read_only: bool = True):
        self.engine = engine
        if read_only:
            event.listens_for(engine, "connect")(
                lambda conn, _: conn.cursor().execute("SET SESSION TRANSACTION READ ONLY"))

    def fetch(self, name: str, **params) -> pd.DataFrame:
        q = QUERIES[name]
        p = q.params(**params).model_dump()
        sql = sql_text(name)
        if "rgs_mode" in p:
            sql = sql.format(rgs_mode=p.pop("rgs_mode"))
        stmt = text(sql)
        for k, v in p.items():
            if isinstance(v, list):
                stmt = stmt.bindparams(bindparam(k, expanding=True))
        with self.engine.connect() as conn:
            return pd.read_sql(stmt, conn, params=p)

    # writes — moved verbatim from data/interface.py; require read_only=False
    def add_prescription_staging_entry(self, entry: PrescriptionStagingRow) -> int | None: ...
    def add_recsys_metric_entry(self, entry: RecsysMetricsRow) -> int | None: ...
```

### `http.py`

```python
import io, requests, pandas as pd
from rgs_interface.registry import QUERIES

class HttpBackend:
    def __init__(self, base_url: str, token: str, timeout: float = 120):
        self.base, self.timeout = base_url.rstrip("/"), timeout
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}",
                               "Accept": "application/vnd.apache.parquet"})

    def fetch(self, name: str, **params) -> pd.DataFrame:
        p = QUERIES[name].params(**params).model_dump(exclude_none=True)
        r = self.s.get(f"{self.base}/v1/{name}", params=p, timeout=self.timeout)
        r.raise_for_status()
        return pd.read_parquet(io.BytesIO(r.content))
```

`requests` serialises list values as repeated params (`patient_ids=1&patient_ids=2`).
Retries on 502/503/504 via `urllib3.Retry` on the session adapter — 5 lines, not shown.

### `server.py`

```python
import io, os
import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from pydantic import TypeAdapter, ValidationError
from rgs_interface.db import get_db_engine
from rgs_interface.registry import QUERIES
from rgs_interface.sql import SqlBackend

app = FastAPI(title="RGS DB API", version="1")
db = SqlBackend(get_db_engine())
TOKENS = dict(t.split(":") for t in os.environ["API_TOKENS"].split(","))   # "token:consumer,..."
VALIDATE = os.environ.get("API_VALIDATE", "1") == "1"

def auth(authorization: str = Header()):
    tok = authorization.removeprefix("Bearer ").strip()
    if tok not in TOKENS:
        raise HTTPException(401)
    return TOKENS[tok]

def make_handler(name, q):
    async def handler(request: Request, consumer: str = Depends(auth)):
        raw = {}
        for k in request.query_params.keys():
            v = request.query_params.getlist(k)
            raw[k] = v if len(v) > 1 or k.endswith("_ids") else v[0]
        params = q.params(**raw)                 # 422 on error via FastAPI
        df = db.fetch(name, **params.model_dump())
        if VALIDATE:                             # API_VALIDATE=0 to skip; default on
            try:
                TypeAdapter(list[q.row]).validate_python(df.to_dict(orient="records"))
            except ValidationError as e:
                log.error("contract violation on %s: %s", name, e.errors()[:3])
                raise HTTPException(500, f"{name}: response does not match {q.row.__name__}")
        if "parquet" in request.headers.get("accept", ""):
            buf = io.BytesIO(); df.to_parquet(buf, index=False)
            return Response(buf.getvalue(), media_type="application/vnd.apache.parquet")
        return {"rows": df.to_dict(orient="records"), "count": len(df)}
    return handler

for name, q in QUERIES.items():
    app.add_api_route(f"/v1/{name}", make_handler(name, q), methods=["GET"], name=name,
                      response_model=list[q.row])   # typed rows in openapi.json

@app.get("/v1/health")
def health():
    db.fetch("protocols")
    return {"status": "ok"}
```

JSON dates: pandas `Timestamp` → FastAPI's encoder emits ISO strings. cdss-alert already
treats dates as strings (`dateStrings: true`), so nothing changes for it.

Validation cost: pydantic v2 validates ~1M flat rows/s. `rgs_data` for the whole cohort is
tens of thousands of rows → milliseconds. `API_VALIDATE=0` exists as an escape hatch, not
a plan.

### `tests/test_contract.py`

```python
import pytest
from pandas.testing import assert_frame_equal
from rgs_interface.registry import QUERIES

SAMPLE = {  # minimal valid params per query against the seed
    "cohort": {}, "protocols": {}, "staging": {"patient_ids": [1, 2]}, ...
}

@pytest.mark.parametrize("name", QUERIES)
def test_sql_http_parity(name, sql_backend, http_backend):
    a = sql_backend.fetch(name, **SAMPLE[name])
    b = http_backend.fetch(name, **SAMPLE[name])
    assert_frame_equal(a, b)
    assert tuple(a.columns) == QUERIES[name].columns
    TypeAdapter(list[QUERIES[name].row]).validate_python(a.to_dict(orient="records"))
```

`http_backend` fixture points at `fastapi.testclient.TestClient(server.app)` through a
tiny adapter, so the test exercises auth, param parsing, row validation and parquet with
no mocks.

## Migration steps

1. Delete `data/preprocess.py`, dead `.sql`, `data/interface.py`. Move `schemas.py` up.
2. `models.py`, `registry.py` + `queries/*.sql` from `API_ENDPOINTS.md`.
3. `sql.py` (lift `_fetch` + the two writes), `http.py`.
4. `server.py`, `Dockerfile`, `docker-compose.yml`.
5. `tests/` — fixture + parity test.
6. `cli.py`: drop `list_patients`/`_save_rgs_data`; `fetch` → `rgs-cli fetch <name> --patient-ids …`.
7. `pyproject.toml`: 1.0.0, deps/extras above, drop poetry-specific sections if moving to hatchling.
8. Tag `v1.0.0`. CHANGELOG: `DatabaseInterface` removed (use `SqlBackend`), `preprocess` removed, extras.

## Versioning

- `/v1` ⇔ major 1. A field added to a row model is minor; removed/renamed/retyped is major.
- Supervisor `cloudbuild.yaml` `_RGS_INTERFACE_REF` and the server image pin the same tag.
- `ai-cdss` stays on `v0.4.1` until it opts in.

## Open decisions

| question | default |
|---|---|
| keep `rgs_mode=app` tables? | yes |
| cohort column names: snake_case (alert) is canonical; supervisor renames on ingest | yes |
| `ClinicalTrialRow` / `PeRow` exact fields | `extra="allow"` until `DESCRIBE` / first run on new host, then lock to `forbid` |
| writes over HTTP | not in v1; `HttpBackend` has no write methods |
| auth | `Authorization: Bearer`, one token per consumer, `API_TOKENS` env |

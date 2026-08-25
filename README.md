# rgs-interface

The RGS database contract, two interchangeable backends, and the RGS DB API server —
one package.

```
registry.py   name → Query(params, row) | Write(body); SQL in queries/<name>.sql, writes/<name>.sql
models.py     the contract: read rows (validated on every API response) + write bodies + enums
sql.py        SqlBackend(engine).fetch(name, **params) / .write(name, body)   — direct MySQL
http.py       HttpBackend(url, token).fetch(...) / .write(...)                — via the API
server.py     FastAPI app: GET /v1/<name> per query, POST /v1/<name> per write   [server]
cli.py        rgs-cli: credentials, fetch <name>, list-patients                   [cli]
```

Endpoint reference: [`docs/API_ENDPOINTS.md`](docs/API_ENDPOINTS.md).
Design and decisions: [`docs/API_CONTRACT_PLAN.md`](docs/API_CONTRACT_PLAN.md).

## Install

```sh
pip install "rgs-interface[http] @ git+https://github.com/dabadav/rgs-interface@v1.0.0"   # clients
pip install "rgs-interface[sql]  @ git+https://github.com/dabadav/rgs-interface@v1.0.0"   # direct DB
pip install "rgs-interface[server] @ git+https://github.com/dabadav/rgs-interface@v1.0.0" # API host
uv tool install "rgs-interface[cli] @ git+https://github.com/dabadav/rgs-interface@v1.0.0" # rgs-cli
```

Core has no database or HTTP dependency — only pandas, pyarrow and pydantic.

## Use

```python
from rgs_interface import HttpBackend, SqlBackend

db = HttpBackend("https://api.rgs.example", token)          # anywhere
# db = SqlBackend.from_config()                             # where 3306 is reachable
# both also accept explicit args: SqlBackend(engine), HttpBackend(url, token)
# raw engine without a backend: rgs_interface.config.make_engine()

cohort = db.fetch("cohort", exclude_control=True, active=True)
staged = db.fetch("staging", patient_ids=[4378], week=4)
rgs    = db.fetch("rgs_data", patient_ids=[4378], rgs_mode="plus")

from rgs_interface.models import PrescriptionStagingRow
new_id = db.write("staging", PrescriptionStagingRow(...))   # needs an rw token
```

Query names, parameters and columns are the registry: `rgs_interface.QUERIES`.
Unknown names raise `KeyError`; bad parameters raise `pydantic.ValidationError`.

## CLI

```sh
rgs-cli credentials set                      # API url + token → ~/.rgs_config.yaml
rgs-cli fetch cohort -p exclude_control=true
rgs-cli fetch staging -p patient_ids=4378,4380 -p week=4 -o staging.csv
rgs-cli list-patients --hospital 7 --hospital 8
rgs-cli fetch rgs_data -p patient_ids=4378 --direct   # bypass the API
```

## Run the API

On the database host (reaches MySQL on `127.0.0.1:3306`):

```sh
cp .env.example .env      # DB_*, API_TOKENS="token:consumer:r|rw,..."
docker compose up -d      # listens on :8000 — put Caddy/nginx with TLS in front
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/v1/health
```

- `Accept: application/vnd.apache.parquet` → parquet (Python clients); otherwise JSON
  `{"rows": [...], "count": n}`.
- Every read response is validated against its row model; a mismatch returns 500 and is
  logged. `API_VALIDATE=0` disables — an escape hatch, not a setting.
- `POST` needs an `rw` token. Give the MySQL user `SELECT` on the tables in
  `docs/API_ENDPOINTS.md` and `INSERT` on `prescription_staging`, `recsys_metrics` only.
- OpenAPI with typed rows at `/openapi.json`, docs at `/docs`.

## Add a query

1. `src/rgs_interface/queries/<name>.sql` — binds `:param`; optional list filters as
   `(:ids_any = 0 OR col IN :ids)`; `{rgs_mode}` for table suffix.
2. A param model and a row model.
3. One line in `QUERIES`. The route, client method and OpenAPI entry follow.

## Tests

```sh
uv venv --python 3.12 && uv pip install -e ".[dev]"
pytest                                   # registry + server (stub backend)
RGS_TEST_DB_URL=mysql+pymysql://ro:pw@host/global_prod pytest tests/test_contract_db.py   # parity vs a real DB
```

## Versioning

`/v1` ⇔ major 1. Adding a field to a row model is minor; removing, renaming or retyping
one is major. Servers and clients pin the same tag.

## Migrating from 0.4.x

`DatabaseInterface` is gone. `DatabaseInterface()` → `SqlBackend.from_config(read_only=False)`;
`fetch_rgs_data(ids, rgs_mode)` → `fetch("rgs_data", patient_ids=ids, rgs_mode=rgs_mode)`;
`fetch_dm_data` → `fetch("dm_data", ...)`; `fetch_patients_by_study([s])` →
`fetch("clinical_trials", study_id=s, due_today=True)`; `add_prescription_staging_entry(row)` →
`write("staging", row)`; `add_recsys_metric_entry(row)` → `write("recsys_metrics", row)`.
Writes now raise on failure instead of returning `None`.

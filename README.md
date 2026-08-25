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

## Deploy the API (Arsys VPS hosting the database)

The API runs on the database host itself, so MySQL is reached on `127.0.0.1:3306` and
port 3306 stays closed to the outside. Only 80/443 are exposed, via Caddy with automatic
Let's Encrypt certificates.

### 0. Prerequisites (once)

- SSH access to the server; Docker + Compose installed
  (`curl -fsSL https://get.docker.com | sh`).
- A DNS `A` record, e.g. `api.rgs.eodyne.com` → server IP.
- Firewall: allow `22`, `80`, `443`; keep `3306` closed.
- A MySQL user for the API (run as root on the server):

```sql
CREATE USER 'api_user'@'localhost' IDENTIFIED BY '<strong password>';
GRANT SELECT ON global_prod.patient                        TO 'api_user'@'localhost';
GRANT SELECT ON global_prod.patient_aisn_data              TO 'api_user'@'localhost';
GRANT SELECT ON global_prod.hospital                       TO 'api_user'@'localhost';
GRANT SELECT ON global_prod.clinical_trials                TO 'api_user'@'localhost';
GRANT SELECT ON global_prod.prescription_plus              TO 'api_user'@'localhost';
GRANT SELECT ON global_prod.session_plus                   TO 'api_user'@'localhost';
GRANT SELECT ON global_prod.recording_plus                 TO 'api_user'@'localhost';
GRANT SELECT ON global_prod.difficulty_modulators_plus     TO 'api_user'@'localhost';
GRANT SELECT ON global_prod.performance_estimators_plus    TO 'api_user'@'localhost';
GRANT SELECT ON global_prod.protocol                       TO 'api_user'@'localhost';
GRANT SELECT ON global_prod.protocol_type                  TO 'api_user'@'localhost';
GRANT SELECT, INSERT ON global_prod.prescription_staging   TO 'api_user'@'localhost';
GRANT SELECT, INSERT ON global_prod.recsys_metrics         TO 'api_user'@'localhost';
-- add the *_app tables too if rgs_mode=app is used
FLUSH PRIVILEGES;
```

### 1. Install

```sh
ssh user@server
sudo mkdir -p /opt/rgs-interface && sudo chown $USER /opt/rgs-interface
git clone --branch v1.0.0 https://github.com/dabadav/rgs-interface /opt/rgs-interface   # private: use a PAT or deploy key
cd /opt/rgs-interface
cp .env.example .env && chmod 600 .env
```

Edit `.env`:

```
API_DOMAIN=api.rgs.eodyne.com
DB_HOST=127.0.0.1
DB_USER=api_user
DB_PASS=<password from step 0>
DB_NAME=global_prod
API_TOKENS=<tok1>:supervisor:r,<tok2>:alert:r,<tok3>:aicdss:rw     # openssl rand -hex 24 for each
```

### 2. Verify against the real data before exposing anything

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh          # if uv is missing
uv venv --python 3.12 .venv && uv pip install -e ".[dev]"
RGS_TEST_DB_URL="mysql+pymysql://api_user:${DB_PASS}@127.0.0.1/global_prod" .venv/bin/pytest -q
```

`tests/test_contract_db.py` runs every query directly and through the API and checks the
rows against the models. A failure names the query and the offending column — fix the
model (or the SQL) before going on.

### 3. Start

```sh
docker compose up -d --build
docker compose logs -f api            # first request logs "supervisor cohort rows=…"
curl https://api.rgs.eodyne.com/v1/health -H "Authorization: Bearer <tok1>"
```

Caddy obtains the certificate on first request; allow ~30 s.

### 4. Hand out

- Supervisor (Cloud Run): env `RGS_API_URL=https://api.rgs.eodyne.com`, secret `RGS_API_TOKEN=<tok1>`.
- Alert (Cloudflare Worker): `DB_API_URL`, secret `DB_API_TOKEN=<tok2>`.
- ai-cdss (when upgraded): `<tok3>` — the only `rw` token.

### Update

```sh
cd /opt/rgs-interface && git fetch --tags && git checkout v1.1.0
docker compose up -d --build            # rebuilds the image, restarts the api; caddy untouched
```

Rollback = `git checkout <previous tag>` + the same command.

### Operate

- `docker compose logs -f api` — one line per request: consumer, query, row count.
- 401 = bad token, 403 = read-only token on POST, 422 = bad params, 500 with a model name =
  data no longer matches the contract (check `DESCRIBE` on that table).
- `API_VALIDATE=0` in `.env` disables response validation — for emergencies only.
- Secrets never leave the server: `.env` is `chmod 600` and git-ignored.

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

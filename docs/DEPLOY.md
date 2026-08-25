# Deploy the RGS DB API

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

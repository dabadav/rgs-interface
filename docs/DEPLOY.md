# Deploy the RGS DB API

Runs on the database host as a normal system service. No Docker. Needs Python 3.12,
`uv`, and the existing nginx.

## 1. MySQL user

```sql
CREATE USER 'api_user'@'localhost' IDENTIFIED BY '<password>';
GRANT SELECT ON global_prod.* TO 'api_user'@'localhost';
GRANT INSERT ON global_prod.prescription_staging TO 'api_user'@'localhost';
GRANT INSERT ON global_prod.recsys_metrics       TO 'api_user'@'localhost';
FLUSH PRIVILEGES;
```

## 2. Install

```sh
git clone --branch v1.0.0 https://github.com/dabadav/rgs-interface /opt/rgs-interface
cd /opt/rgs-interface
uv venv --python 3.12 .venv && uv pip install ".[server]"
cp .env.example .env && chmod 600 .env
```

Edit `.env`:

```
PORT=8000
DB_HOST=127.0.0.1
DB_USER=api_user
DB_PASS=<password>
DB_NAME=global_prod
API_TOKENS=<token1>:supervisor:r,<token2>:alert:r,<token3>:aicdss:rw
```

## 3. Tokens

The API has no user accounts. Each client program gets one secret string (a token) and
sends it on every request as `Authorization: Bearer <token>`. The server accepts a request
only if the token is in `API_TOKENS`.

`API_TOKENS` is a comma-separated list of `token:name:scope`:

- `token`: any random string. Generate one per client with `openssl rand -hex 24`.
- `name`: a label for the log lines (`supervisor`, `alert`, `aicdss`). Not checked, just printed.
- `scope`: `r` = read only (GET), `rw` = may also write (POST). Only ai-cdss writes.

Give each client its own token so one can be revoked without touching the others. To
revoke or rotate: edit `API_TOKENS`, `systemctl restart rgs-api`, update the client.
The tokens live only in `.env` on this server and in each client's secret store.

## 4. Check before exposing

```sh
RGS_TEST_DB_URL="mysql+pymysql://api_user:<password>@127.0.0.1/global_prod" .venv/bin/python -m pytest -q
```

Runs every query directly and through the API and checks the columns and types. If
something fails it names the query; fix before continuing.

## 5. Service

Set `User=` in `deploy/rgs-api.service` to the account that owns `/opt/rgs-interface`
(same as your other services), then:

```sh
sudo cp deploy/rgs-api.service /etc/systemd/system/
sudo systemctl enable --now rgs-api
curl -H "Authorization: Bearer <tok1>" http://127.0.0.1:8000/v1/health
```

## 6. nginx

Either a subdomain or a path under the existing site. See `deploy/nginx.conf`. For a
path, also set `ROOT_PATH=/rgs-api` in `.env` and restart the service. TLS with
`certbot --nginx` as for the other sites.

## Update

```sh
cd /opt/rgs-interface && git fetch --tags && git checkout v1.1.0
uv pip install ".[server]"
sudo systemctl restart rgs-api
```

Rollback: check out the previous tag and repeat.

## Operate

- Logs: `journalctl -u rgs-api -f`. One line per request: consumer, query, rows.
- 401 bad token, 403 read-only token on POST, 422 bad parameters, 500 with a model name:
  data no longer matches the contract.
- Hand each client its URL and token. Supervisor: `RGS_API_URL`, `RGS_API_TOKEN`.
  Alert: `DB_API_URL`, `DB_API_TOKEN`. People using `rgs-cli`: `rgs-cli credentials set`.

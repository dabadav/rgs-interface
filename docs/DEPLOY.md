# Deploy the RGS DB API

## 1. MySQL user

A dedicated account for the API, limited to what it does: read any table, insert into the
two tables ai-cdss writes. Even with a stolen token, or a bug in the API, nothing else on
the database can be changed. It connects from `localhost` only, so it is unusable from
outside the server.

```sql
CREATE USER 'api_user'@'localhost' IDENTIFIED BY '<password>';
GRANT SELECT ON global_prod.* TO 'api_user'@'localhost';
GRANT INSERT ON global_prod.prescription_staging TO 'api_user'@'localhost';
GRANT INSERT ON global_prod.recsys_metrics       TO 'api_user'@'localhost';
FLUSH PRIVILEGES;
```

## 2. Install

```sh
curl -fsSL https://raw.githubusercontent.com/dabadav/rgs-interface/v1.0.0/deploy/install.sh | sudo sh
```

What it does, in order: installs `uv` if missing, creates the `rgsapi` system user, installs
`rgs-interface[server]` into `/opt/rgs-api/.venv`, asks for the MySQL password and writes
`/opt/rgs-api/.env` (mode 600) with one fresh token per client, installs and starts the
`rgs-api` systemd service, and checks `/v1/health`. It prints the tokens once; hand each to
its client.

The resulting `.env`:

```
PORT=8000
DB_HOST=127.0.0.1
DB_USER=api_user
DB_PASS=<password>
DB_NAME=global_prod
API_TOKENS=<token1>:supervisor:r,<token2>:alert:r,<token3>:aicdss:rw
API_VALIDATE=1
```

Variables: `RGS_REF` (version tag, default `v1.0.0`), `RGS_DIR` (`/opt/rgs-api`),
`RGS_USER` (`rgsapi`). If nginx will serve the API under a path, add `ROOT_PATH=/rgs-api`
to `.env` and `systemctl restart rgs-api`.

## 3. Tokens

The API has no user accounts. Each client program gets one secret string (a token) and
sends it on every request as `Authorization: Bearer <token>`. The server accepts a request
only if the token is in `API_TOKENS`.

`API_TOKENS` is a comma-separated list of `token:name:scope`:

- `token`: a random string. `server init` generates them; by hand, `openssl rand -hex 24`.
- `name`: a label for the log lines (`supervisor`, `alert`, `aicdss`). Not checked, just printed.
- `scope`: `r` = read only (GET), `rw` = may also write (POST). Only ai-cdss writes.

Give each client its own token so one can be revoked without touching the others. To
revoke or rotate: edit `API_TOKENS`, `systemctl restart rgs-api`, update the client.
The tokens live only in `.env` on this server and in each client's secret store.

## 4. Service

The installer wrote `/etc/systemd/system/rgs-api.service`, running as `rgsapi` (only that
user can read `.env`):

```ini
[Unit]
Description=RGS DB API
Wants=network-online.target
After=network-online.target mysql.service mariadb.service

[Service]
User=rgsapi
WorkingDirectory=/opt/rgs-api
EnvironmentFile=/opt/rgs-api/.env
ExecStart=/opt/rgs-api/.venv/bin/uvicorn rgs_interface.server:app --host 127.0.0.1 --port ${PORT}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```sh
systemctl status rgs-api
curl -H "Authorization: Bearer <token1>" http://127.0.0.1:8000/v1/health
```

## 5. nginx

Either a subdomain or a path under the existing site. TLS with `certbot --nginx` as for
the other sites.

Subdomain:

```nginx
server {
    listen 80;
    server_name api.rgs.eodyne.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_read_timeout 120s;
    }
}
```

Path under the existing site (also set `ROOT_PATH=/rgs-api` in `.env` and restart):

```nginx
location /rgs-api/ {
    proxy_pass http://127.0.0.1:8000/;
    proxy_set_header Host $host;
    proxy_read_timeout 120s;
}
```

## Update

Same one-liner with the new tag; `.env` is kept.

```sh
curl -fsSL https://raw.githubusercontent.com/dabadav/rgs-interface/v1.1.0/deploy/install.sh | sudo RGS_REF=v1.1.0 sh
```

Rollback: same with the previous tag.

## Operate

- Logs: `journalctl -u rgs-api -f`. One line per request: consumer, query, rows.
- 401 bad token, 403 read-only token on POST, 422 bad parameters, 500 with a model name:
  data no longer matches the contract.
- Hand each client its URL and token. Supervisor: `RGS_API_URL`, `RGS_API_TOKEN`.
  Alert: `DB_API_URL`, `DB_API_TOKEN`. People using `rgs-cli`: `rgs-cli credentials set`.

## Verifying against the real data (developers)

Before the first deploy, from any machine with SSH to the server:

```sh
ssh -L 3306:127.0.0.1:3306 user@server        # in one terminal
RGS_TEST_DB_URL="mysql+pymysql://api_user:<password>@127.0.0.1/global_prod" pytest tests/test_contract_db.py
```

Runs every query directly and through the API and checks columns and types.

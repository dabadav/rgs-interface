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
mkdir -p /opt/rgs-api && cd /opt/rgs-api && uv venv --python 3.12 .venv && uv pip install "rgs-interface[server] @ git+https://github.com/dabadav/rgs-interface@v1.0.0" && .venv/bin/rgs-cli server init
```

`server init` asks for the MySQL password, generates one token per client, and writes
`/opt/rgs-api/.env` (mode 600). It prints the tokens once; hand each to its client.
Flags: `--db-user`, `--db-name`, `--port`, `--root-path /rgs-api` (if nginx serves the API
under a path), `--force` to overwrite.

The resulting file:

```
PORT=8000
DB_HOST=127.0.0.1
DB_USER=api_user
DB_PASS=<password>
DB_NAME=global_prod
API_TOKENS=<token1>:supervisor:r,<token2>:alert:r,<token3>:aicdss:rw
API_VALIDATE=1
```

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

Run the API as its own system user so only it can read `.env`. Print the unit for this
directory and install it (`--user` if your convention differs):

```sh
sudo useradd -r -s /usr/sbin/nologin rgsapi
sudo chown -R rgsapi /opt/rgs-api
.venv/bin/rgs-cli server init --unit | sudo tee /etc/systemd/system/rgs-api.service
```

It looks like this:

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
sudo systemctl enable --now rgs-api
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

```sh
cd /opt/rgs-api
uv pip install "rgs-interface[server] @ git+https://github.com/dabadav/rgs-interface@v1.1.0"
sudo systemctl restart rgs-api
```

Rollback: same command with the previous tag.

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

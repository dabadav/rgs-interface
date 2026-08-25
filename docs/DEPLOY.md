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
sudo useradd -r -s /usr/sbin/nologin rgsapi
sudo git clone --branch v1.0.0 https://github.com/dabadav/rgs-interface /opt/rgs-interface
cd /opt/rgs-interface
sudo -u rgsapi uv venv --python 3.12 .venv
sudo -u rgsapi uv pip install ".[server]"
sudo cp .env.example .env && sudo chown rgsapi .env && sudo chmod 600 .env
```

Edit `/opt/rgs-interface/.env`:

```
PORT=8000
DB_HOST=127.0.0.1
DB_USER=api_user
DB_PASS=<password>
DB_NAME=global_prod
API_TOKENS=<tok1>:supervisor:r,<tok2>:alert:r,<tok3>:aicdss:rw
```

Tokens: `openssl rand -hex 24`, one per consumer. `rw` only for ai-cdss.

## 3. Check before exposing

```sh
sudo -u rgsapi env $(cat .env | xargs) RGS_TEST_DB_URL="mysql+pymysql://api_user:<password>@127.0.0.1/global_prod" \
  .venv/bin/python -m pytest -q
```

Runs every query directly and through the API and checks the columns and types. If
something fails it names the query; fix before continuing.

## 4. Service

```sh
sudo cp deploy/rgs-api.service /etc/systemd/system/
sudo systemctl enable --now rgs-api
curl -H "Authorization: Bearer <tok1>" http://127.0.0.1:8000/v1/health
```

## 5. nginx

Either a subdomain or a path under the existing site. See `deploy/nginx.conf`. For a
path, also set `ROOT_PATH=/rgs-api` in `.env` and restart the service. TLS with
`certbot --nginx` as for the other sites.

## Update

```sh
cd /opt/rgs-interface && sudo git fetch --tags && sudo git checkout v1.1.0
sudo -u rgsapi uv pip install ".[server]"
sudo systemctl restart rgs-api
```

Rollback: check out the previous tag and repeat.

## Operate

- Logs: `journalctl -u rgs-api -f`. One line per request: consumer, query, rows.
- 401 bad token, 403 read-only token on POST, 422 bad parameters, 500 with a model name:
  data no longer matches the contract.
- Consumers get the URL and their token. Supervisor: `RGS_API_URL`, `RGS_API_TOKEN`.
  Alert: `DB_API_URL`, `DB_API_TOKEN`.

#!/bin/sh
# RGS DB API installer for the database host. Run as root:
#   curl -fsSL https://raw.githubusercontent.com/dabadav/rgs-interface/v1.0.0/deploy/install.sh | sudo sh
# Re-running upgrades the package to $RGS_REF and restarts the service; .env is kept.
#   RGS_REF=v1.1.0   version tag to install (default v1.0.0)
#   RGS_DIR          install dir (default /opt/rgs-api)
#   RGS_USER         service user (default rgsapi)
set -eu

REF="${RGS_REF:-v1.0.0}"
DIR="${RGS_DIR:-/opt/rgs-api}"
SVC_USER="${RGS_USER:-rgsapi}"
UNIT=/etc/systemd/system/rgs-api.service

[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo)"; exit 1; }

if ! command -v uv >/dev/null 2>&1; then
    echo "> installing uv"
    curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=/usr/local/bin sh >/dev/null
fi

id "$SVC_USER" >/dev/null 2>&1 || useradd -r -s /usr/sbin/nologin "$SVC_USER"

echo "> installing rgs-interface $REF into $DIR"
mkdir -p "$DIR" && cd "$DIR"
[ -d .venv ] || uv venv -q --python 3.12 .venv
uv pip install -q --python .venv/bin/python "rgs-interface[server] @ git+https://github.com/dabadav/rgs-interface@$REF"

if [ ! -f .env ]; then
    echo "> creating .env"
    .venv/bin/rgs-cli server init </dev/tty
fi

.venv/bin/rgs-cli server init --unit --user "$SVC_USER" > "$UNIT"
chown -R "$SVC_USER" "$DIR"
systemctl daemon-reload
systemctl enable -q rgs-api
systemctl restart rgs-api
sleep 2

PORT=$(sed -n 's/^PORT=//p' .env)
TOKEN=$(sed -n 's/^API_TOKENS=//p' .env | cut -d: -f1)
if curl -fsS -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:${PORT}/v1/health" >/dev/null; then
    echo "> rgs-api is up on 127.0.0.1:${PORT}. Next: nginx (see docs/DEPLOY.md, step 5)."
else
    echo "> service did not answer; check: journalctl -u rgs-api -n 50"
    exit 1
fi

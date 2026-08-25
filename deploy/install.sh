#!/bin/sh
# RGS DB API installer for the database host. Run as root.
#
#   curl -fsSLO https://raw.githubusercontent.com/dabadav/rgs-interface/v1.0.0/deploy/install.sh
#   less install.sh          # read it
#   sudo sh install.sh
#
# Writes ONLY:
#   /usr/local/bin/uv, uvx                 if uv is absent (binary only: no PATH edits, no updater)
#   system user $RGS_USER                  if absent
#   $RGS_DIR/**                            venv, Python, uv cache, .env (never overwritten)
#   /etc/systemd/system/rgs-api.service    if absent or already ours
# Nothing under /root, /home or any existing Python environment is read or written.
# Re-running upgrades the package to $RGS_REF and restarts the service; .env is kept.
#
#   RGS_REF    version tag (default v1.0.0)
#   RGS_DIR    install dir, must be /opt/<name> or /srv/<name> (default /opt/rgs-api)
#   RGS_USER   service user (default rgsapi)
#   RGS_PORT   local port (default 8000; only used when creating .env)
set -eu

REF="${RGS_REF:-v1.0.0}"
DIR="${RGS_DIR:-/opt/rgs-api}"
SVC_USER="${RGS_USER:-rgsapi}"
PORT_DEFAULT="${RGS_PORT:-8000}"
UNIT=/etc/systemd/system/rgs-api.service

die() { echo "install.sh: $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "run as root (sudo sh install.sh)"
command -v curl >/dev/null 2>&1 || die "curl is required"
command -v git  >/dev/null 2>&1 || die "git is required (uv installs the package from GitHub)"
command -v systemctl >/dev/null 2>&1 || die "systemd is required"

# --- install dir guard: only /opt/<name> or /srv/<name>; existing dir must be ours or empty
case "$DIR" in
    /opt/?*|/srv/?*) ;;
    *) die "RGS_DIR must be /opt/<name> or /srv/<name>, got '$DIR'" ;;
esac
case "$DIR" in */) die "RGS_DIR must not end with /" ;; esac
if [ -d "$DIR" ] && [ ! -d "$DIR/.venv" ] && [ -n "$(ls -A "$DIR" 2>/dev/null)" ]; then
    die "$DIR exists and is not an rgs-api install (no .venv); refusing to touch it"
fi

# --- unit guard: never overwrite someone else's unit
if [ -f "$UNIT" ] && ! grep -q '^Description=RGS DB API' "$UNIT"; then
    die "$UNIT exists and is not ours; refusing to overwrite"
fi

# --- uv: unmanaged install = binary only, no shell rc edits, no self-updater
if ! command -v uv >/dev/null 2>&1; then
    echo "> installing uv to /usr/local/bin"
    curl -LsSf https://astral.sh/uv/install.sh | UV_UNMANAGED_INSTALL=/usr/local/bin sh >/dev/null
    export PATH="/usr/local/bin:$PATH"
fi

id "$SVC_USER" >/dev/null 2>&1 || useradd -r -s /usr/sbin/nologin "$SVC_USER"

# keep everything uv downloads inside $DIR so chown covers it and /root stays untouched
export UV_PYTHON_INSTALL_DIR="$DIR/python"
export UV_CACHE_DIR="$DIR/.cache"

echo "> installing rgs-interface $REF into $DIR"
mkdir -p "$DIR" && cd "$DIR"
[ -d .venv ] || uv venv -q --python 3.12 .venv
uv pip install -q --python .venv/bin/python "rgs-interface[server] @ git+https://github.com/dabadav/rgs-interface@$REF"

if [ ! -f .env ]; then
    # --- port guard, only when we are the ones choosing the port
    if command -v ss >/dev/null 2>&1 && ss -ltn 2>/dev/null | awk '{print $4}' | grep -q ":${PORT_DEFAULT}\$"; then
        die "port $PORT_DEFAULT is already in use; set RGS_PORT to a free port"
    fi
    echo "> creating .env"
    .venv/bin/rgs-cli server init --port "$PORT_DEFAULT" </dev/tty
fi

.venv/bin/rgs-cli server init --unit --user "$SVC_USER" > "$UNIT"
chown -R "$SVC_USER" "$DIR"
chmod 600 "$DIR/.env"
systemctl daemon-reload
systemctl enable -q rgs-api
systemctl restart rgs-api
sleep 2

PORT=$(sed -n 's/^PORT=//p' .env)
TOKEN=$(sed -n 's/^API_TOKENS=//p' .env | cut -d: -f1)
if curl -fsS -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:${PORT}/v1/health" >/dev/null; then
    echo "> rgs-api is up on 127.0.0.1:${PORT}. Next: nginx (docs/DEPLOY.md, step 5)."
else
    die "service did not answer; check: journalctl -u rgs-api -n 50"
fi

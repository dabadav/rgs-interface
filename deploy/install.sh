#!/bin/sh
# RGS DB API installer for the database host. Run as root.
#
#   curl -fsSL https://raw.githubusercontent.com/dabadav/rgs-interface/v1.0.0-rc4/deploy/install.sh | sudo sh
#   ... | sudo RGS_DRY_RUN=1 sh        show checks and plan, change nothing
#   ... | sudo sh -s uninstall         remove everything this script created
#
# Before changing anything it: checks prerequisites, snapshots the trial's files
# (~/.rgs_config.yaml, ~/.ai_cdss, .env, the existing rgs-cli), prints its plan and
# asks for confirmation. Afterwards it re-checks the snapshot and reports any difference.
#
# Writes ONLY:
#   /usr/local/bin/uv, uvx                 if uv is absent (binary only: no PATH edits, no updater)
#   system user $RGS_USER                  if absent
#   $RGS_DIR/**                            venv, Python, uv cache, .env (never overwritten)
#   /etc/systemd/system/rgs-api.service    if absent or already ours
#
#   RGS_REF    version tag (default v1.0.0-rc4)
#   RGS_DIR    install dir, /opt/<name> or /srv/<name> (default /opt/rgs-api)
#   RGS_USER   service user (default rgsapi)
#   RGS_PORT   local port (default 8000; only used when creating .env)
#   RGS_YES=1  skip the confirmation prompt
set -eu

REF="${RGS_REF:-v1.0.0-rc4}"
DIR="${RGS_DIR:-/opt/rgs-api}"
SVC_USER="${RGS_USER:-rgsapi}"
PORT_DEFAULT="${RGS_PORT:-8000}"
DRY="${RGS_DRY_RUN:-0}"
UNIT=/etc/systemd/system/rgs-api.service
SNAP=/tmp/rgs-api-install.before

die() { echo "install.sh: $*" >&2; exit 1; }
say() { echo "> $*"; }
run() { if [ "$DRY" = 1 ]; then echo "  [dry-run] $*"; else "$@"; fi; }

[ "$(id -u)" -eq 0 ] || die "run as root (sudo)"

# ------------------------------------------------------------------ uninstall
if [ "${1:-}" = "uninstall" ]; then
    say "removing rgs-api (service, $DIR, user $SVC_USER). Nothing else is touched."
    run systemctl disable --now rgs-api 2>/dev/null || true
    [ -f "$UNIT" ] && grep -q '^Description=RGS DB API' "$UNIT" && run rm -f "$UNIT"
    run systemctl daemon-reload
    [ -d "$DIR/.venv" ] && run rm -rf "$DIR"
    id "$SVC_USER" >/dev/null 2>&1 && run userdel "$SVC_USER"
    say "done. uv was left in place (/usr/local/bin/uv); remove by hand if unwanted."
    exit 0
fi

# ------------------------------------------------------------------ pre-flight (read-only)
say "pre-flight"
command -v curl >/dev/null 2>&1 || die "curl is required"
command -v git  >/dev/null 2>&1 || die "git is required (the package is installed from GitHub)"
command -v systemctl >/dev/null 2>&1 || die "systemd is required"
case "$DIR" in /opt/?*|/srv/?*) ;; *) die "RGS_DIR must be /opt/<name> or /srv/<name>, got '$DIR'" ;; esac
case "$DIR" in */) die "RGS_DIR must not end with /" ;; esac
if [ -d "$DIR" ] && [ ! -d "$DIR/.venv" ] && [ -n "$(ls -A "$DIR" 2>/dev/null)" ]; then
    die "$DIR exists and is not an rgs-api install; refusing to touch it"
fi
if [ -f "$UNIT" ] && ! grep -q '^Description=RGS DB API' "$UNIT"; then
    die "$UNIT exists and is not ours; refusing to overwrite"
fi
if [ ! -f "$DIR/.env" ] && command -v ss >/dev/null 2>&1 && ss -ltn 2>/dev/null | awk '{print $4}' | grep -q ":${PORT_DEFAULT}\$"; then
    die "port $PORT_DEFAULT is in use; set RGS_PORT to a free port"
fi
FRESH_UV=0; command -v uv >/dev/null 2>&1 || FRESH_UV=1
FRESH_USER=0; id "$SVC_USER" >/dev/null 2>&1 || FRESH_USER=1
EXISTING_CLI="$(command -v rgs-cli 2>/dev/null || true)"
printf '  uv: %s   user %s: %s   %s: %s   unit: %s   existing rgs-cli: %s\n' \
    "$( [ $FRESH_UV = 1 ] && echo 'will install' || echo present)" \
    "$SVC_USER" "$( [ $FRESH_USER = 1 ] && echo 'will create' || echo present)" \
    "$DIR" "$( [ -d "$DIR/.venv" ] && echo 'present (upgrade)' || echo 'will create')" \
    "$( [ -f "$UNIT" ] && echo 'ours (rewrite)' || echo 'will create')" \
    "${EXISTING_CLI:-none on PATH}"

# ------------------------------------------------------------------ snapshot of the trial's files
snapshot() {
    for h in /root "$( [ -n "${SUDO_USER:-}" ] && getent passwd "$SUDO_USER" | cut -d: -f6 )"; do
        [ -n "$h" ] || continue
        for f in "$h/.rgs_config.yaml" "$h/.ai_cdss" "$h/.env"; do
            [ -e "$f" ] && find "$f" -type f -exec sha256sum {} +
        done
    done
    [ -n "$EXISTING_CLI" ] && find "$(dirname "$EXISTING_CLI")" -maxdepth 1 -type f -exec sha256sum {} +
    return 0
}
snapshot | sort > "$SNAP"
say "snapshot of $(wc -l < "$SNAP") trial files taken ($SNAP)"

# ------------------------------------------------------------------ plan + confirm
say "plan"
cat <<PLAN
  1. $( [ $FRESH_UV = 1 ] && echo "install uv to /usr/local/bin (binary only)" || echo "use existing uv: $(command -v uv)")
  2. $( [ $FRESH_USER = 1 ] && echo "useradd -r $SVC_USER" || echo "reuse user $SVC_USER")
  3. $DIR/.venv  <-  rgs-interface[server] @ $REF   (Python and cache inside $DIR)
  4. $( [ -f "$DIR/.env" ] && echo "keep existing $DIR/.env" || echo "create $DIR/.env (asks MySQL password, generates tokens, port $PORT_DEFAULT)")
  5. write $UNIT, chown -R $SVC_USER $DIR, systemctl enable --now rgs-api
  6. curl http://127.0.0.1:<port>/v1/health, re-check the snapshot
PLAN
[ "$DRY" = 1 ] && { say "dry run: nothing changed."; exit 0; }
if [ "${RGS_YES:-0}" != 1 ]; then
    printf 'Proceed? [y/N] '; read -r ans </dev/tty
    [ "$ans" = y ] || [ "$ans" = Y ] || die "aborted, nothing changed"
fi

# ------------------------------------------------------------------ install
if [ $FRESH_UV = 1 ]; then
    say "installing uv"
    curl -LsSf https://astral.sh/uv/install.sh | UV_UNMANAGED_INSTALL=/usr/local/bin sh >/dev/null
    export PATH="/usr/local/bin:$PATH"
fi
[ $FRESH_USER = 1 ] && useradd -r -s /usr/sbin/nologin "$SVC_USER"

export UV_PYTHON_INSTALL_DIR="$DIR/python" UV_CACHE_DIR="$DIR/.cache"
say "installing rgs-interface $REF into $DIR"
mkdir -p "$DIR" && cd "$DIR"
[ -d .venv ] || uv venv -q --python 3.12 .venv
uv pip install -q --python .venv/bin/python "rgs-interface[server] @ git+https://github.com/dabadav/rgs-interface@$REF"

if [ ! -f .env ]; then
    say "creating .env"
    .venv/bin/rgs-cli server init --port "$PORT_DEFAULT" </dev/tty
fi

.venv/bin/rgs-cli server init --unit --user "$SVC_USER" > "$UNIT"
chown -R "$SVC_USER" "$DIR"
chmod 600 "$DIR/.env"
systemctl daemon-reload
systemctl enable -q rgs-api
systemctl restart rgs-api
sleep 2

# ------------------------------------------------------------------ verify
PORT=$(sed -n 's/^PORT=//p' .env)
TOKEN=$(sed -n 's/^API_TOKENS=//p' .env | cut -d: -f1)
if curl -fsS -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:${PORT}/v1/health" >/dev/null; then
    say "rgs-api is up on 127.0.0.1:${PORT}"
else
    echo "install.sh: service did not answer; check: journalctl -u rgs-api -n 50" >&2
fi
if snapshot | sort | cmp -s - "$SNAP"; then
    say "trial files unchanged (snapshot matches)"
else
    echo "install.sh: WARNING trial files differ from snapshot; compare with: snapshot vs $SNAP" >&2
    snapshot | sort | diff "$SNAP" - || true
    exit 1
fi
say "next: nginx (docs/DEPLOY.md, step 5)"

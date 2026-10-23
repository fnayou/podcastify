#!/bin/sh
set -e

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"
PUBLIC_ROOT="${PUBLIC_ROOT:-/app/public}"
PODCASTS_ROOT="${PODCASTS_ROOT:-/app/podcasts}"
CACHE_ROOT="${CACHE_ROOT:-/app/.cache}"

owned() {
  [ "$(stat -c %u:%g "$1")" = "${PUID}:${PGID}" ]
}

claim() {
  path="$1"
  shift
  if ! owned "$path"; then
    chown "$@" "${PUID}:${PGID}" "$path" \
      || echo "⚠️  Could not chown ${path}; continuing (check bind-mount perms)"
  fi
}

echo "🔧 Podcastify container starting..."

# Two supported runtimes:
#   1. Hardened: operator pins the container user (compose `user: "1000:1000"`)
#      so it starts non-root. Compatible with `cap_drop: ALL` + `read_only`
#      because no privileged ops are needed — bind-mounts must already be owned
#      by that uid. We just run as the current user.
#   2. Convenience: container starts as root (default). We chown only what the
#      app writes (cache, public/ itself, public/*.xml) to PUID/PGID, never the
#      media or podcast configs, and drop privileges with su-exec. Adapts to any host
#      bind-mount owner (NAS/desktop), but needs CHOWN/SETUID/SETGID caps.
if [ "$(id -u)" = "0" ]; then
  echo "🔐 Started as root; preparing dirs and dropping to ${PUID}:${PGID}."
  mkdir -p "$PUBLIC_ROOT" "$PODCASTS_ROOT" "$CACHE_ROOT"
  claim "$CACHE_ROOT" -R
  claim "$PUBLIC_ROOT"
  for feed in "$PUBLIC_ROOT"/*.xml; do
    if [ -e "$feed" ]; then
      claim "$feed"
    fi
  done
  RUNAS="su-exec ${PUID}:${PGID}"
else
  echo "ℹ️  Started as uid $(id -u); skipping chown/su-exec (hardened mode)."
  RUNAS=""
fi

if [ "${RUN_ON_START:-true}" = "true" ]; then
  echo "🎙️  Running generator at startup..."
  if ! $RUNAS python /app/app.py generate; then
    echo "⚠️  Generator exited non-zero; continuing to serve existing content"
  fi
fi

echo "🌐 Starting Caddy on :${SERVICE_PORT:-8080}"

# Caddy is the only long-running process and logs to stdout itself, so it runs
# in the foreground directly — no supervisor. tini is PID 1 for the whole
# container life (Dockerfile ENTRYPOINT) and forwards signals to this script,
# then to Caddy; $RUNAS is empty in hardened mode, su-exec in root mode.
exec $RUNAS caddy run --config /etc/caddy/Caddyfile --adapter caddyfile

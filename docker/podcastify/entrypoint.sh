#!/bin/sh
set -e

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

echo "🔧 Podcastify container starting..."

# Two supported runtimes:
#   1. Hardened: operator pins the container user (compose `user: "1000:1000"`)
#      so it starts non-root. Compatible with `cap_drop: ALL` + `read_only`
#      because no privileged ops are needed — bind-mounts must already be owned
#      by that uid. We just run as the current user.
#   2. Convenience: container starts as root (default). We chown the writable
#      dirs to PUID/PGID and drop privileges with su-exec. Adapts to any host
#      bind-mount owner (NAS/desktop), but needs CHOWN/SETUID/SETGID caps.
if [ "$(id -u)" = "0" ]; then
  echo "🔐 Started as root; preparing dirs and dropping to ${PUID}:${PGID}."
  mkdir -p /app/public /app/podcasts /app/.cache
  chown -R "${PUID}:${PGID}" /app/.cache /app/public /app/podcasts 2>/dev/null \
    || echo "⚠️  Could not chown data dirs; continuing (check bind-mount perms)"
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
# in the foreground directly — no supervisor. tini stays PID 1 (reaps zombies,
# forwards signals); $RUNAS is empty in hardened mode, su-exec in root mode.
exec /sbin/tini -- $RUNAS caddy run --config /etc/caddy/Caddyfile --adapter caddyfile

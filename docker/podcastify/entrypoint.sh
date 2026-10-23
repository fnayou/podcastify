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

if [ "${1:-}" = "generate" ]; then
  shift
  exec $RUNAS python /app/app.py generate "$@"
fi

run_on_start="$(printf '%s' "${RUN_ON_START:-true}" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')"
case "$run_on_start" in
  true|yes|1|on) run_on_start=true ;;
esac

generate_interval="$(printf '%s' "${GENERATE_INTERVAL:-0}" | tr -d '[:space:]')"
case "$generate_interval" in
  ''|*[!0-9]*)
    echo "⚠️  GENERATE_INTERVAL='${GENERATE_INTERVAL}' is not a whole number of seconds; auto-regeneration off"
    generate_interval=0
    ;;
esac

watch_args=""
if [ "$run_on_start" = "true" ]; then
  echo "🎙️  Running generator at startup..."
  if ! $RUNAS python /app/app.py generate; then
    echo "⚠️  Generator exited non-zero; continuing to serve existing content"
    watch_args="--initial-run"
  fi
fi

if [ "$generate_interval" -gt 0 ]; then
  echo "🔁 Checking configs and media for changes every ${generate_interval}s"
  $RUNAS python /app/app.py watch --interval "$generate_interval" $watch_args &
fi

echo "🌐 Starting Caddy on :${SERVICE_PORT:-8080}"

# Caddy runs in the foreground and logs to stdout itself — no supervisor. tini
# is PID 1 for the whole container life (Dockerfile ENTRYPOINT), forwards
# signals to this script, then to Caddy, and reaps the optional background
# watcher, which stops with the container when Caddy exits; $RUNAS is empty in
# hardened mode, su-exec in root mode.
exec $RUNAS caddy run --config /etc/caddy/Caddyfile --adapter caddyfile

# Caddy binary from the official image. The alpine `caddy` package lags
# upstream (2.10.0) and bundles old Go deps flagged by Docker Scout; the
# official image ships the patched release built with the current Go toolchain.
FROM caddy:2.11.7-alpine AS caddy

FROM python:3.12-alpine3.22

# System deps (keep small, versions pinned to alpine 3.22 stable).
# `apk upgrade` patches base OS packages (e.g. openssl 3.5.6-r0 -> 3.5.7-r0).
# su-exec: drop from root to PUID/PGID at runtime (entrypoint).
# hadolint ignore=DL3018
RUN apk upgrade --no-cache && apk add --no-cache \
    tini \
    su-exec \
    ca-certificates

# Statically-linked Caddy binary; no shared-lib deps, safe to copy standalone.
COPY --from=caddy /usr/bin/caddy /usr/bin/caddy

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App + configs
COPY app.py /app/
COPY podcastify/ /app/podcastify/
COPY docker/podcastify/Caddyfile        /etc/caddy/Caddyfile
COPY docker/podcastify/entrypoint.sh    /entrypoint.sh

# Ensure entrypoint is executable and LF line endings
RUN chmod 0755 /entrypoint.sh && sed -i 's/\r$//' /entrypoint.sh

# Pre-create the data dirs (normally bind-mounted at runtime). The entrypoint
# chowns only what the app writes (cache, public/ itself, public/*.xml) to
# PUID/PGID before dropping privileges.
RUN mkdir -p /app/public /app/podcasts /app/.cache

# Defaults (override via compose/.env)
# PUID/PGID default to 1000 and are honored by the entrypoint; set them to match
# the host bind-mount owner (server, NAS, desktop) so generated files aren't
# written as root. Caddy data/config land under XDG_* (the cache volume) and
# supervisord logs/pid under /tmp, so nothing writes to the read-only root FS.
ENV SERVICE_PORT=8080 \
  PUBLIC_BASE_URL=http://localhost:8080 \
  PODCASTS_ROOT=/app/podcasts \
  PUBLIC_ROOT=/app/public \
  CACHE_ROOT=/app/.cache \
  RUN_ON_START=true \
  GENERATE_INTERVAL=0 \
  PUBLISH_XML=true \
  PUBLISH_INDEX=false \
  LOG_LEVEL=INFO \
  PYTHONUNBUFFERED=1 \
  PUID=1000 \
  PGID=1000 \
  HOME=/app \
  XDG_DATA_HOME=/app/.cache/caddy \
  XDG_CONFIG_HOME=/app/.cache/caddy

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=120s CMD ["/bin/sh", "-c", "wget -q --spider http://127.0.0.1:${SERVICE_PORT}/healthz || exit 1"]

ENTRYPOINT ["/sbin/tini", "--", "/entrypoint.sh"]

FROM python:3.12-alpine3.22

# System deps (keep small, versions pinned to alpine 3.22 stable)
# su-exec: drop from root to PUID/PGID at runtime (entrypoint).
RUN apk add --no-cache \
    caddy \
    ffmpeg \
    tini \
    su-exec \
    ca-certificates

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

# Pre-create the writable dirs (normally bind-mounted at runtime). The
# entrypoint chowns them to PUID/PGID before dropping privileges.
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
  PUBLISH_XML=true \
  LOG_LEVEL=INFO \
  PYTHONUNBUFFERED=1 \
  PUID=1000 \
  PGID=1000 \
  HOME=/app \
  XDG_DATA_HOME=/app/.cache/caddy \
  XDG_CONFIG_HOME=/app/.cache/caddy

EXPOSE 8080

HEALTHCHECK CMD wget -q -O- http://localhost:${SERVICE_PORT}/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]

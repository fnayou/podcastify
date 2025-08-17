FROM python:3.12-alpine3.22

# System deps (keep small)
RUN apk add --no-cache caddy ffmpeg supervisor tini ca-certificates

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App + configs
COPY app.py /app/
COPY docker/podcastify/Caddyfile        /etc/caddy/Caddyfile
COPY docker/podcastify/supervisord.conf /etc/supervisord.conf
COPY docker/podcastify/entrypoint.sh    /entrypoint.sh

# Ensure entrypoint is executable and LF line endings
RUN chmod 0755 /entrypoint.sh && sed -i 's/\r$//' /entrypoint.sh

# Defaults (override via compose/.env)
ENV SERVICE_PORT=8080 \
  PUBLIC_BASE_URL=http://localhost:8080 \
  PODCASTS_ROOT=/app/podcasts \
  PUBLIC_ROOT=/app/public \
  RUN_ON_START=true \
  PUBLISH_XML=true

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]

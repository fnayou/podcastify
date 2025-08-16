# Combined image: Python (generator) + Caddy (static server)
FROM python:3.12-alpine

LABEL org.opencontainers.image.authors="Aymen FNAYOU <fnayou.aymen@gmail.com>"
LABEL org.opencontainers.image.title="PodCastify"
LABEL org.opencontainers.image.description="Create private podcast feeds from your own MP3s with zero fuss."
LABEL org.opencontainers.image.source="https://github.com/fnayou/podcastify"

# system packages
RUN apk add --no-cache caddy ffmpeg

WORKDIR /app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt || pip install --no-cache-dir PyYAML


# copy generator from project root into image
COPY app.py /app/app.py

# copy caddy config from repo
COPY docker/podcastify/Caddyfile /etc/caddy/Caddyfile

# prepare directories
RUN mkdir -p /app/public /app/podcasts

# environment defaults
ENV PORT=8080 \
  PUBLIC_BASE_URL=http://localhost:8080 \
  PODCASTS_ROOT=/app/podcasts \
  PUBLIC_ROOT=/app/public \
  RUN_ON_START=true \
  PUBLISH_XML=true
# EXPOSE 8080  # (optional, informational only)

# simple entrypoint: optionally run generator, then start caddy
COPY docker/podcastify/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

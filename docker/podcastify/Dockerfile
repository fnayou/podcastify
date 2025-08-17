FROM python:3.12-alpine3.21


RUN apk add --no-cache --update caddy ffmpeg \
  && apk upgrade --no-cache

RUN addgroup -S app && adduser -S -G app -u 10001 app \
  && mkdir -p /app/public /app/podcasts /config /data \
  && chown -R app:app /app /config /data


COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app.py /app/app.py
COPY docker/podcastify/Caddyfile /etc/caddy/Caddyfile
COPY docker/podcastify/entrypoint.sh /entrypoint.sh
COPY docker/podcastify/supervisord.conf /etc/supervisord.conf

ENV PORT=8080 \
  PODCASTS_ROOT=/app/podcasts \
  PUBLIC_ROOT=/app/public \
  RUN_ON_START=true \
  PUBLISH_XML=true

USER app
EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]

# Deployment

## Quick Run from Docker Hub

Image: `fnayou/podcastify` (public)

```bash
export HOST_PORT=1234
export PUBLIC_BASE_URL="http://localhost:${HOST_PORT}"

docker run --rm \
  -e SERVICE_PORT=8080 \
  -e PUBLIC_BASE_URL="${PUBLIC_BASE_URL}" \
  -p ${HOST_PORT}:8080 \
  -v "$(pwd)/public:/app/public" \
  -v "$(pwd)/podcasts:/app/podcasts" \
  fnayou/podcastify:latest
```

## Docker Compose

```yaml
services:
  podcastify:
    image: fnayou/podcastify:latest
    ports:
      - "${HOST_PORT:-8080}:${SERVICE_PORT:-8080}"
    environment:
      - SERVICE_PORT=${SERVICE_PORT:-8080}
      - PUBLIC_BASE_URL=${PUBLIC_BASE_URL:-http://localhost:${HOST_PORT:-8080}}
      - PODCASTS_ROOT=/app/podcasts
      - PUBLIC_ROOT=/app/public
      - RUN_ON_START=${RUN_ON_START:-true}
      - PUBLISH_XML=${PUBLISH_XML:-true}
    volumes:
      - ./public:/app/public
      - ./podcasts:/app/podcasts
    restart: unless-stopped
```

Create a `.env` file:

```env
HOST_PORT=8080
SERVICE_PORT=8080
PUBLIC_BASE_URL=http://localhost:${HOST_PORT}
RUN_ON_START=true
PUBLISH_XML=true
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HOST_PORT` | `8080` | Host port exposed to the outside. |
| `SERVICE_PORT` | `8080` | Container port Caddy listens on. |
| `PUBLIC_BASE_URL` | `http://localhost:8080` | Base URL used in generated enclosure and image links. |
| `PODCASTS_ROOT` | `/app/podcasts` | In-container path to podcast configs. |
| `PUBLIC_ROOT` | `/app/public` | In-container path to media and generated feeds. |
| `RUN_ON_START` | `true` | Run generator on container startup. |
| `PUBLISH_XML` | `true` | Write XML files to disk. |
| `LOG_LEVEL` | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, or `ERROR`. |
| `OPENCODE_CONFIG` | `.opencode/opencode.json` | Path to [OpenCode](https://opencode.ai) config (agents, skills, instructions). Contributor-only; not required to run the container. |

## Log Visibility

The podcastify generator logs at different levels. The visibility depends on how the generator is invoked:

| How generator runs | In `docker compose logs -f`? | Why |
|---|---|---|
| Boot, `RUN_ON_START=true` | YES | entrypoint runs generator as PID-1 chain before `exec supervisord`; stdout inherited by container |
| Caddy / supervisord | YES | `supervisord.conf:10-13` forwards `/dev/stdout`+`/dev/stderr`, `maxbytes=0` |
| `docker compose exec podcastify python /app/app.py generate` | NO | separate process attached to the exec client's terminal, not PID 1 — prints in your shell |
| `docker compose run --rm ...` | NO | separate temporary container, its own log stream |

**Note**: On-demand `exec` generation will not show in the main service log stream. Check your shell terminal for the output, or re-run the generator at boot by restarting the container.

## Reverse Proxy

For production behind a reverse proxy at `https://podcasts.domain.tld`:

1. Set `PUBLIC_BASE_URL=https://podcasts.domain.tld` in `.env`
2. Forward to the container's `${SERVICE_PORT}` (default 8080)

### Caddy Example

```
podcasts.domain.tld {
  reverse_proxy localhost:8080
}
```

### Nginx Example

```nginx
server {
  listen 443 ssl http2;
  server_name podcasts.domain.tld;

  location / {
    proxy_pass http://localhost:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }
}
```

## Security Hardening

For v1.0.0 and later, add these Compose settings without changing the image:

```yaml
services:
  podcastify:
    # ... existing config ...
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true
    cap_drop: ["ALL"]
```

Root filesystem read-only. Mounted `public/` + `podcasts/` stay writable. Prevents privilege escalation; drops Linux capabilities. Note: generator writes cache + temp files to `PUBLIC_ROOT` — any hardening must keep `public/` writable.

## Caddyfile

Shipped Caddyfile uses `{$SERVICE_PORT}` and hides dotfiles:

```caddy
:{$SERVICE_PORT} {
  root * /app/public
  encode gzip
  header Access-Control-Allow-Origin "*"

  @rss path *.xml
  header @rss Content-Type "application/rss+xml; charset=utf-8"
  header @rss Cache-Control "public, max-age=300, must-revalidate"

  @mp3 path *.mp3
  header @mp3 Cache-Control "public, max-age=31536000, immutable"
  header @mp3 Content-Type "audio/mpeg"

  @images path *.jpg *.jpeg *.png *.webp
  header @images Cache-Control "public, max-age=86400"

  file_server {
    browse
    hide .*
  }

  log {
    output stdout
    format console
  }
}
```

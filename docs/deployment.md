# Deployment

## Quick Run from Docker Hub

Image: `fnayou/podcastify` (public)

```bash
export HOST_PORT=1234
export PUBLIC_BASE_URL="http://localhost:${HOST_PORT}"

docker run --rm \
  -e PORT=8080 \
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
      - "${HOST_PORT:-8080}:${PORT:-8080}"
    environment:
      - PORT=${PORT:-8080}
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
PORT=8080
PUBLIC_BASE_URL=http://localhost:${HOST_PORT}
RUN_ON_START=true
PUBLISH_XML=true
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HOST_PORT` | `8080` | Host port exposed to the outside. |
| `PORT` | `8080` | Container port Caddy listens on. |
| `PUBLIC_BASE_URL` | `http://localhost:8080` | Base URL used in generated enclosure and image links. |
| `PODCASTS_ROOT` | `/app/podcasts` | In-container path to podcast configs. |
| `PUBLIC_ROOT` | `/app/public` | In-container path to media and generated feeds. |
| `RUN_ON_START` | `true` | Run generator on container startup. |
| `PUBLISH_XML` | `true` | Write XML files to disk. |
| `OPENCODE_CONFIG` | `.ai/opencode.json` | Path to [OpenCode](https://opencode.ai) config (agents, skills, instructions). Contributor-only; not required to run the container. |

## Reverse Proxy

For production behind a reverse proxy at `https://podcasts.domain.tld`:

1. Set `PUBLIC_BASE_URL=https://podcasts.domain.tld` in `.env`
2. Forward to the container's `${PORT}` (default 8080)

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

These make the root filesystem read-only (mounted `public/` and `podcasts/` remain writable), prevent privilege escalation, and drop Linux capabilities.

If running as a non-root user (future versions):

```yaml
services:
  podcastify:
    user: "10001:10001"
```

## Caddyfile

The image ships with a Caddyfile that uses `{$PORT}` and hides `.gitkeep`:

```caddy
:{$PORT} {
  root * /app/public
  encode gzip
  header Access-Control-Allow-Origin "*"

  file_server {
    browse
    hide .gitkeep
  }

  log {
    output stdout
    format console
  }
}
```

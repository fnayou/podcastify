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
  -v "$(pwd)/cache:/app/.cache" \
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
      - SERVICE_PORT
      - PUBLIC_BASE_URL=${PUBLIC_BASE_URL:-http://localhost:${HOST_PORT:-8080}}
      - RUN_ON_START
      - PUBLISH_XML
      - LOG_LEVEL
      - PUID
      - PGID
    volumes:
      - ./public:/app/public
      - ./podcasts:/app/podcasts
      - ./cache:/app/.cache
    restart: unless-stopped
```

Create a `.env` file:

```env
HOST_PORT=8080
SERVICE_PORT=8080
PUBLIC_BASE_URL=http://localhost:${HOST_PORT}
RUN_ON_START=true
PUBLISH_XML=true
LOG_LEVEL=INFO
PUID=1000
PGID=1000
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HOST_PORT` | `8080` | Host port exposed to the outside. |
| `SERVICE_PORT` | `8080` | Container port Caddy listens on. |
| `PUBLIC_BASE_URL` | `http://localhost:8080` | Base URL used in generated enclosure and image links. |
| `PUID` | `1000` | uid the container drops to when started as root. Match the owner of the bind-mounts. |
| `PGID` | `1000` | gid the container drops to when started as root. |
| `RUN_ON_START` | `true` | Run generator on container startup. Accepts `true/yes/1/on`, case-insensitive; any other value skips it. |
| `PUBLISH_XML` | `true` | Write XML files to disk. Accepts `true/yes/1/on` and `false/no/0/off`; other values warn and count as false. |
| `LOG_LEVEL` | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, or `ERROR`. |

Compose passes these through from `.env` or your shell. A variable you leave unset takes the image default shown above.

The paths inside the container are fixed: `/app/public`, `/app/podcasts` and `/app/.cache`. To keep your data elsewhere on the host, change the left side of the volume mounts in `docker-compose.yml` (see [ADR 0004](adr/0004-path-env-vars-are-internal.md)).

## Log Visibility

The podcastify generator logs at different levels. The visibility depends on how the generator is invoked:

| How generator runs | In `docker compose logs -f`? | Why |
|---|---|---|
| Boot, `RUN_ON_START=true` | YES | `entrypoint.sh` runs the generator under `tini` (PID 1) before `exec`-ing Caddy; stdout is inherited by the container |
| Caddy | YES | Caddy runs in the foreground under `tini` and logs to stdout |
| `docker compose exec podcastify /entrypoint.sh generate` | NO | separate process attached to the exec client's terminal, not PID 1 — prints in your shell. Runs as `PUID`/`PGID` like the boot run, so files are never root-owned |
| `docker compose run --rm podcastify generate` | NO | separate temporary container, its own log stream |

**Note**: On-demand `exec` generation will not show in the main service log stream. Check your shell terminal for the output, or re-run the generator at boot by restarting the container.

## Reverse Proxy

For production behind a reverse proxy at `https://podcasts.domain.tld`:

1. Set `PUBLIC_BASE_URL=https://podcasts.domain.tld` in `.env`
2. Forward to the container's `${SERVICE_PORT}` (default 8080)
3. Publish the port on the loopback interface only, so the plain-HTTP port is not reachable from the LAN or internet around the proxy:

```yaml
    ports:
      - "127.0.0.1:${HOST_PORT:-8080}:${SERVICE_PORT:-8080}"
```

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

The image supports two runtimes (see [runtime](runtime.md)):

- **Default:** starts as root, chowns `public/`, `podcasts/` and `.cache/` to `PUID`/`PGID`, then drops privileges with `su-exec`. Needs the `CHOWN`, `SETUID` and `SETGID` capabilities, so do not combine it with `cap_drop: ["ALL"]`.
- **Hardened:** pin the container user. The entrypoint then skips chown and `su-exec`. The bind-mounts must already be owned by that uid.

```yaml
services:
  podcastify:
    # ... existing config ...
    user: "1000:1000"
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true
    cap_drop: ["ALL"]
```

The root filesystem is read-only. `public/`, `podcasts/` and `cache/` stay writable bind-mounts, and Caddy keeps its data under the cache mount (`/app/.cache`). The cache is outside `public/`, so it is never served.

## Caddyfile

Shipped Caddyfile uses `{$SERVICE_PORT}`, turns the admin API off, serves a fixed `/healthz` response for the container healthcheck, does not list directories, and hides dotfiles. Responses carry `X-Content-Type-Options: nosniff` and no `Server` header. MP3s are cached for one day without `immutable`, so an episode fixed in place under the same filename reaches listeners within a day:

```caddy
{
  admin off
}

:{$SERVICE_PORT} {
  root * /app/public

  @health path /healthz
  respond @health "ok" 200
  log_skip @health
  encode gzip
  header Access-Control-Allow-Origin "*"
  header X-Content-Type-Options "nosniff"
  header -Server

  @rss path *.xml
  header @rss Content-Type "application/rss+xml; charset=utf-8"
  header @rss Cache-Control "public, max-age=300, must-revalidate"

  @mp3 path *.mp3
  header @mp3 Cache-Control "public, max-age=86400"
  header @mp3 Content-Type "audio/mpeg"

  @images path *.jpg *.jpeg *.png *.webp
  header @images Cache-Control "public, max-age=86400"

  file_server {
    hide .*
  }

  log {
    output stdout
    format console
  }
}
```

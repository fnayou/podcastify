# Podcastify — tiny self-hosted podcast RSS generator

[![Docker Pulls](https://img.shields.io/docker/pulls/fnayou/podcastify)](https://hub.docker.com/r/fnayou/podcastify)
[![Image Size](https://img.shields.io/docker/image-size/fnayou/podcastify/latest)](https://hub.docker.com/r/fnayou/podcastify/tags)
[![GitHub Stars](https://img.shields.io/github/stars/fnayou/podcastify)](https://github.com/fnayou/podcastify)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

Create private podcast feeds from your own MP3s with minimal setup. Drop MP3s into a folder, add a simple YAML file, and Podcastify builds an iTunes-compatible RSS feed. Serve everything (XML + media) from one container (Caddy + Python) via Docker.

- GitHub repository: **https://github.com/fnayou/podcastify**
- Docker Hub image: **https://hub.docker.com/r/fnayou/podcastify**
- Docker Hub profile: **https://hub.docker.com/u/fnayou**
- Author GitHub: **https://github.com/fnayou**

---

## Features

- Simple layout: `./podcasts/*.yaml` for configs, `./public/<name>/` for media and images.
- Auto-discovery of episodes if you omit the `episodes:` list.
- MP3 duration extraction via `ffprobe` (falls back gracefully).
- iTunes fields: author, owner, subtitle, summary, explicit, categories, episode types, seasons.
- Clean XML: stable GUIDs (SHA-1), configurable language, empty tags rather than empty CDATA.
- Single container image: Caddy (static hosting) + Python generator.
- Developer-friendly Taskfile with commands like `task up`, `task generate`, `task logs`.
- Configurable ports: choose any host port (e.g., `1234`) via `.env` / Compose. Caddy listens on `${PORT}` inside the container.

---

## Run from Docker Hub

Image: `fnayou/podcastify` (public)

### Quick run

```bash
# choose host port and base URL
export HOST_PORT=1234
export PUBLIC_BASE_URL="http://localhost:${HOST_PORT}"

docker run --rm   -e PORT=8080   -e PUBLIC_BASE_URL="${PUBLIC_BASE_URL}"   -p ${HOST_PORT}:8080   -v "$(pwd)/public:/app/public"   -v "$(pwd)/podcasts:/app/podcasts"   fnayou/podcastify:latest
# or pin a version:
# fnayou/podcastify:v1.0.0
```

### docker-compose.yml

```yaml
services:
  podcastify:
    image: fnayou/podcastify:latest   # or fnayou/podcastify:v1.0.0
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

Create a `.env` file (next section) to set `HOST_PORT` and `PUBLIC_BASE_URL`.

For production behind a reverse proxy at `https://podcasts.domain.tld`, set `PUBLIC_BASE_URL=https://podcasts.domain.tld` and forward to the container’s `${PORT}` (default 8080).

---

## Directory structure

```
.
├─ app.py                # generator (root of the project; already in the image)
├─ docker-compose.yml
├─ docker/               # Dockerfile & Caddy config (only needed for local builds)
│  └─ podcastify/
│     ├─ Dockerfile
│     ├─ Caddyfile       # uses :{$PORT} and hides .gitkeep (see below)
│     └─ entrypoint.sh
├─ podcasts/             # <name>-podcast.yaml lives here
│  └─ example-podcast.yaml
├─ public/               # served statically by Caddy
│  └─ example/
│     ├─ cover.jpg
│     ├─ ep01.mp3
│     └─ episode.png
├─ Taskfile.yml
├─ .env                  # optional env vars
├─ .gitignore
└─ README.md
```

- Configs go in `./podcasts` as `name-podcast.yaml`.
- Media and images live in `./public/<name>/`.
- The feed is generated to `./public/<name>.xml`.

---

## Requirements

- Docker and Docker Compose
- [Task](https://taskfile.dev) (go-task) for convenient commands — optional if you just use `docker compose`
- Linux watchers (optional): `inotifywait` from `inotify-tools`
- YAML linter (optional): `yamllint`

---

## Environment variables (.env)

```env
# Host port → visit http://localhost:${HOST_PORT}
HOST_PORT=8080

# Container listen port (Caddy listens on this; keep 8080 unless you know why)
PORT=8080

# Base URL used in generated <enclosure> and image links
# Must reflect the public URL and host port you expose (or your domain)
PUBLIC_BASE_URL=http://localhost:${HOST_PORT}

# (Advanced) override in-container paths if needed
PODCASTS_ROOT=/app/podcasts
PUBLIC_ROOT=/app/public

# Run generator on container start (default true)
RUN_ON_START=true

# Write XML to disk (default true)
PUBLISH_XML=true
```

By default, Caddy serves `./public`. Change the published host port via `HOST_PORT` in `.env` or directly in `docker-compose.yml`.

---

## Caddyfile example

The image ships with a Caddyfile that uses an environment variable for the port and hides `.gitkeep` from listings:

```caddy
:{$PORT} {
  root * /app/public
  encode gzip
  header Access-Control-Allow-Origin "*"

  file_server {
    browse
    hide .gitkeep
    # hide .git* .DS_Store  # optionally hide more dotfiles
  }

  log {
    output stdout
    format console
  }
}
```

---

## Security hardening

The image runs fine as-is. For additional defense-in-depth, you can apply these Compose settings with **v1.0.0 and later** without changing the image:

```yaml
services:
  podcastify:
    # ... your existing config ...
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true
    cap_drop: ["ALL"]
```

These settings make the root filesystem read-only (your mounted `public/` and `podcasts/` remain writable), prevent privilege escalation, and drop Linux capabilities (the app listens on high port `${PORT}` so none are needed).

If you later publish an image that runs as a non-root user by default (for example `v1.0.1+`), you can also add:

```yaml
services:
  podcastify:
    user: "10001:10001"
```

and keep the same hardening flags above.

---

## Quickstart (local development with Taskfile)

1. Clone and configure
   ```bash
   git clone https://github.com/fnayou/podcastify
   cd podcastify
   # create .env from the section above (set HOST_PORT if you want a custom port)
   ```

2. Start the stack
   ```bash
   task up
   ```

3. Create a podcast
   ```bash
   # scaffold a new config: podcasts/myshow-podcast.yaml
   task new NAME=myshow

   # add media under public/myshow/
   mkdir -p public/myshow
   cp /path/to/ep01.mp3 public/myshow/
   cp /path/to/cover.jpg public/myshow/
   ```

4. Generate feeds
   ```bash
   task generate
   ```

5. Subscribe
   - Feed URL: `http://localhost:${HOST_PORT}/myshow.xml`
   - Media files: `http://localhost:${HOST_PORT}/myshow/ep01.mp3`

---

## YAML config example

Minimal example: `podcasts/myshow-podcast.yaml`

```yaml
name: "myshow"
title: "My Private Show"
author-name: "Your Name"
author-email: "you@example.com"
description: "Personal feed for testing"
language: "en"
explicit: false
image: "cover.jpg"   # place in ./public/myshow/cover.jpg
categories:
  - "Technology"
  - ["Society & Culture", "Personal Journals"]

# Optional: list episodes explicitly.
# If omitted, Podcastify will auto-discover *.mp3 in ./public/myshow/
episodes:
  - file: "ep01.mp3"     # basename only is used internally
    title: "Hello World"
    description: "First episode"
    pub_date: "2025-01-01T08:00:00Z"
    image: "episode.png" # optional; resolve from ./public/myshow/
    explicit: false
    season: 1
    episode: 1
    episode_type: "full" # full | trailer | bonus
    guid: "custom-guid-if-you-really-want"  # otherwise auto-generated
```

Notes:

- `file`: only the basename is used; put the MP3 in `public/<name>/`.
- `image` at channel or episode level can be a filename (served from `public/<name>/`) or a full URL.
- Categories input accepted as:
  - `"Technology"`
  - `["Technology", "Education"]`
  - `[["Society & Culture", "Personal Journals"]]`
  - `[{ name: "Technology", sub: "Software How-To" }]`
- If `pub_date` is missing or invalid, the file modification time is used.
- Durations come from `ffprobe`; if that fails, the `<itunes:duration>` tag is omitted.

---

## Task commands

```bash
task                 # show task list
task up              # build and start container
task down            # stop and remove
task restart         # restart
task status          # ps + recent logs

task generate        # run the generator now
task logs            # follow logs
task logs:recent     # recent logs only
task logs:errors     # grep errors/warnings
task shell           # shell into container
task shell:root      # root shell

task new NAME=myshow # scaffold a new config
task generate:watch  # watch ./podcasts (Linux, inotifywait)
task generate:watch-public # watch ./public (Linux, inotifywait)

task clean:feeds     # delete generated XML
task clean:docker    # down + prune
task doctor          # quick env and directory checks
task compose:ps      # docker compose ps
task compose:config  # show resolved compose config
```

---

## How it works

- On `task up`, the container starts Caddy and optionally runs the generator at boot (`RUN_ON_START=true`).
- You can run the generator any time with `task generate`.
- The XML `<generator>` tag is `podcastify`.
- Episode GUIDs default to a SHA-1 of `<podcast>/<filename>` and are not permalinks.

---

## License

MIT — see [`LICENSE`](./LICENSE).

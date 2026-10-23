# Getting Started

## Prerequisites

- Docker and Docker Compose
- [Task](https://taskfile.dev) (go-task) for convenient commands — optional if you just use `docker compose`

## Quickstart

### 1. Clone and configure

```bash
git clone https://github.com/fnayou/podcastify
cd podcastify
cp .env.example .env   # set HOST_PORT if you want a custom port
```

Variables and defaults: [Environment Variables](deployment.md#environment-variables).

### 2. Start the stack

```bash
task docker:up
```

### 3. Create a podcast

```bash
# scaffold a new config: podcasts/myshow-podcast.yaml
task podcastify:new NAME=myshow

# add media under public/myshow/
mkdir -p public/myshow
cp /path/to/ep01.mp3 public/myshow/
cp /path/to/cover.jpg public/myshow/
```

The scaffold has no `episodes:` list, so every `.mp3`, `.m4a`, `.mp4`, `.ogg` and `.opus` file in `public/myshow/` is published, newest first. To pick files or set titles, add an `episodes:` list; a non-empty list turns auto-discovery off (see [Episodes](configuration.md#episodes)).

### 4. Generate feeds

```bash
task podcastify:generate
```

Run it again whenever you add files, or set `GENERATE_INTERVAL` to regenerate automatically (see [Automatic regeneration](runtime.md#automatic-regeneration)).

### 5. Subscribe

- Feed URL: `http://localhost:${HOST_PORT}/myshow.xml`
- Media files: `http://localhost:${HOST_PORT}/myshow/ep01.mp3`

## Next Steps

- [Configuration reference](configuration.md)
- [Deployment guide](deployment.md)
- [Architecture overview](architecture.md)
- [Troubleshooting](troubleshooting.md)
- [Contributing](contributing.md)

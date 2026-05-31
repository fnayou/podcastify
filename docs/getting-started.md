# Getting Started

## Prerequisites

- Docker and Docker Compose
- [Task](https://taskfile.dev) (go-task) for convenient commands — optional if you just use `docker compose`

## Quickstart

### 1. Clone and configure

```bash
git clone https://github.com/fnayou/podcastify
cd podcastify
# create .env from the section above (set HOST_PORT if you want a custom port)
```

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

### 4. Generate feeds

```bash
task podcastify:generate
```

### 5. Subscribe

- Feed URL: `http://localhost:${HOST_PORT}/myshow.xml`
- Media files: `http://localhost:${HOST_PORT}/myshow/ep01.mp3`

## Next Steps

- [Configuration reference](configuration.md)
- [Deployment guide](deployment.md)
- [Architecture overview](architecture.md)
- [Troubleshooting](troubleshooting.md)
- [Contributing](contributing.md)

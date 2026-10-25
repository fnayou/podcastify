# Getting Started

!!! note "This site tracks `main`"
    These pages describe the `latest` image and the `main` branch. For an older version, use the
    [GitHub Releases](https://github.com/fnayou/podcastify/releases) and pin that image tag.

## Prerequisites

- Docker. Docker Compose is optional; the [Deployment](deployment.md#docker-compose) page has a Compose file.

## 1. Run the image

```bash
docker run -d --name podcastify \
  -p 8080:8080 \
  -e PUBLIC_BASE_URL=http://localhost:8080 \
  -v "$(pwd)/podcasts:/app/podcasts" \
  -v "$(pwd)/public:/app/public" \
  -v "$(pwd)/cache:/app/.cache" \
  fnayou/podcastify:latest
```

`PUBLIC_BASE_URL` is the address your podcast app will use to reach the container. Variables and defaults:
[Environment Variables](deployment.md#environment-variables).

## 2. Add a podcast

Create `podcasts/myshow-podcast.yaml`:

```yaml
name: "myshow"
title: "My Private Show"
author-name: "Your Name"
author-email: "you@example.com"
description: "Personal feed for testing"
language: "en"
explicit: false
```

Put the media in `public/myshow/` (add `cover.jpg` and set `image: "cover.jpg"` for artwork):

```bash
mkdir -p public/myshow
cp /path/to/ep01.mp3 public/myshow/
```

The config has no `episodes:` list, so every `.mp3`, `.m4a`, `.mp4`, `.ogg` and `.opus` file in
`public/myshow/` is published, newest first. To pick files or set titles, add an `episodes:` list; a non-empty list
turns auto-discovery off (see [Episodes](configuration.md#episodes)).

## 3. Generate the feed

```bash
docker exec podcastify /entrypoint.sh generate
```

The generator also runs at every container start. Set `GENERATE_INTERVAL` to regenerate automatically when files
change (see [How it works](how-it-works.md#automatic-regeneration)).

## 4. Subscribe

- Feed URL: `http://localhost:8080/myshow.xml`
- Media files: `http://localhost:8080/myshow/ep01.mp3`

## Next steps

- [Configuration reference](configuration.md)
- [Deployment guide](deployment.md)
- [How it works](how-it-works.md)
- [Troubleshooting](troubleshooting.md)

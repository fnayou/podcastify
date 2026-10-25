![podcastify: tiny self-hosted podcast RSS generator](https://raw.githubusercontent.com/fnayou/podcastify/main/website/assets/images/podcastify-readme-banner.svg)

# Podcastify — tiny self-hosted podcast RSS generator

[![Docker Pulls](https://img.shields.io/docker/pulls/fnayou/podcastify)](https://hub.docker.com/r/fnayou/podcastify)
[![Image Size](https://img.shields.io/docker/image-size/fnayou/podcastify/latest)](https://hub.docker.com/r/fnayou/podcastify/tags)
[![GitHub Stars](https://img.shields.io/github/stars/fnayou/podcastify)](https://github.com/fnayou/podcastify)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/fnayou/podcastify/blob/main/LICENSE)

Create private podcast feeds from your own audio files with minimal setup. Drop files into a folder, add a simple YAML file, and Podcastify builds an iTunes-compatible RSS feed. Serve everything (XML and media) from one container (Caddy and Python).

## Quick start

```bash
docker run -d --name podcastify \
  -p 8080:8080 \
  -e PUBLIC_BASE_URL=http://localhost:8080 \
  -v "$(pwd)/podcasts:/app/podcasts" \
  -v "$(pwd)/public:/app/public" \
  -v "$(pwd)/cache:/app/.cache" \
  fnayou/podcastify:latest
```

Then add a podcast: [Getting Started](https://fnayou.github.io/podcastify/getting-started/).

## Features

- Episodes discovered from a folder, or listed explicitly; durations for MP3, M4A, MP4, OGG and Opus.
- iTunes fields, stable GUIDs, clean XML, and a feed file rewritten only when its content changes.
- Optional index page at `/` and automatic regeneration when configs or media change.
- One image, no database, no account.

## Documentation

The documentation site tracks `main`; older versions are in the releases.

- [Getting Started](https://fnayou.github.io/podcastify/getting-started/): install, run, first feed
- [Deployment](https://fnayou.github.io/podcastify/deployment/): Compose, environment variables, reverse proxy, hardening
- [Configuration](https://fnayou.github.io/podcastify/configuration/): the YAML reference
- [How it works](https://fnayou.github.io/podcastify/how-it-works/): the pipeline, the image, permissions
- [Troubleshooting](https://fnayou.github.io/podcastify/troubleshooting/): common issues and fixes
- [Contributing](https://github.com/fnayou/podcastify/blob/main/docs/contributing.md): development setup, style, pull requests
- [Releases](https://github.com/fnayou/podcastify/releases): release notes for each version

## Links

- GitHub: https://github.com/fnayou/podcastify
- Docker Hub: https://hub.docker.com/r/fnayou/podcastify

## License

MIT, see [`LICENSE`](https://github.com/fnayou/podcastify/blob/main/LICENSE).

# Glossary

- **Podcast / channel**: one feed, defined by `podcasts/<name>-podcast.yaml`, served as `public/<name>.xml`.
- **Episode**: one MP3 + metadata, either listed explicitly under `episodes:` or auto-discovered from `public/<name>/*.mp3`.
- **Feed**: generated iTunes-compatible RSS 2.0 XML for a podcast.
- **GUID**: episode unique ID. Defaults to SHA-1(`<podcast_name>/<filename>`), `isPermaLink="false"`.
- **`duration_hms`**: episode duration as `H:MM:SS` or `M:SS`, either set in YAML or computed via `ffprobe`.
- **Duration cache**: persisted ffprobe results at `<PUBLIC_ROOT>/.podcastify-cache.json`, keyed by `(path, mtime)`.
- **`SERVICE_PORT`**: in-container Caddy listen port (env var, default `8080`). Separate from `HOST_PORT` (host-side mapping).
- **`HOST_PORT`**: host port published to outside (compose only, default `8080`).
- **`PUBLIC_BASE_URL`**: env var `PUBLIC_BASE_URL` (key); read into `Config.BASE_URL` (attribute). Embedded in RSS enclosure/image links. Default `http://localhost:8080`.
- **`PUBLIC_ROOT` / `PODCASTS_ROOT`**: env-configured base dirs for media+feeds and YAML configs (defaults `/app/public`, `/app/podcasts`).
- **`RUN_ON_START`**: if true, generator runs once at container boot before Caddy serves content.
- **`PUBLISH_XML`**: if false, validates/discovers episodes but skips writing `<name>.xml` (dry run).
- **`LOG_LEVEL`**: env var controlling logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Default `INFO`. Used by stdlib `logging` module; controls what appears in `docker compose logs`.
- **Channel fields / Episode fields**: whitelisted YAML keys copied into feed metadata — `Config.CHANNEL_FIELDS` / `Config.EPISODE_FIELDS` (`podcastify/config.py:26-36`).

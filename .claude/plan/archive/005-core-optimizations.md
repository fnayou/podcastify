# Core Architecture & Performance Optimizations

## Feature
A suite of high-impact software engineering and performance upgrades for Podcastify. This includes persistent `ffprobe` caching, parallel MP3 processing, dependency cleanup, strict Pydantic YAML validation, Caddy HTTP caching, and modularizing `app.py`.

## Modeling
- **Cache**: A local JSON file (`.podcastify-cache.json`) to persist `MediaProcessor._duration_cache`.
- **Validation**: `pydantic` BaseModel classes representing `PodcastConfig` and `Episode` schemas.
- **Architecture**: Split `app.py` into a package: `podcastify/__init__.py`, `config.py`, `media.py`, `rss.py`, `parser.py`, `cli.py`.
- **Concurrency**: Use `concurrent.futures.ThreadPoolExecutor` in `EpisodeManager`.
- **Caddyfile**: Add `header Cache-Control` directives for static files.

## Constraints
- Existing external interfaces (Docker, CLI commands in `Taskfile.yml`, existing YAML config structures) must not break.
- Pydantic models must gracefully accept and translate legacy fields (e.g., mapping `author` to `author-name`).
- All `tests/` must be updated, refactored for the new modular structure, and pass with `>= 90%` coverage.

## Acceptance
- `feedgen` is entirely removed from `requirements.txt`.
- `ffprobe` durations persist across restarts (subsequent `task generate` runs skip `ffprobe` entirely for known files).
- Multi-file MP3 discovery utilizes parallel threads.
- Caddy serves `.xml` and `.mp3` files with correct HTTP caching headers.
- `app.py` is safely modularized into a dedicated `podcastify/` package structure.
- Incorrect YAML configs fail instantly with clear Pydantic validation errors before generation begins.

## Tasks
- [x] Task 1: Remove `feedgen` from `requirements.txt`.
- [x] Task 2: Refactor `app.py` into the `podcastify/` directory structure (`cli.py`, `config.py`, `media.py`, `parser.py`, `rss.py`).
- [x] Task 3: Implement persistent JSON-based caching for `MediaProcessor` in `podcastify/media.py`.
- [x] Task 4: Introduce `concurrent.futures.ThreadPoolExecutor` for parallel `ffprobe` processing.
- [x] Task 5: Add `pydantic` to dependencies and integrate strict schema models for config validation.
- [x] Task 6: Update `docker/podcastify/Caddyfile` with optimal `Cache-Control` headers for media and XML.
- [x] Task 7: Update all unit and integration tests to support the modular package, then run `task test:coverage` to verify full stability.

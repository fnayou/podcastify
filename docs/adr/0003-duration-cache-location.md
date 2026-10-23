# 0003 - Duration cache location and lifecycle

## Status

Accepted. Implemented: the cache lives under `CACHE_ROOT`, `MediaProcessor` drops
entries for files that no longer exist when it saves, and a cache left in
`PUBLIC_ROOT` is migrated on first load. The on-disk format gained a version in
[ADR 0006](0006-tinytag-for-durations.md).

## Context

`MediaProcessor` used to persist ffprobe results to
`<PUBLIC_ROOT>/.podcastify-cache.json` (`Config.CACHE_FILENAME`).
`PUBLIC_ROOT` (`/app/public`) is the directory Caddy serves
(`root * /app/public` in `docker/podcastify/Caddyfile`). At the time of this
decision there were three problems:

1. The cache file was web-reachable. `hide .*` in the shipped Caddyfile
   returns 404 for direct requests, but the `docs/deployment.md` Caddyfile
   snippet used `hide .gitkeep`, which would expose it.
2. Cache entries for deleted media were never pruned (`_save_disk_cache`
   serialized the full in-memory dict), so the file grew unbounded.
3. `docs/deployment.md` recommends `read_only: true`; the cache only stayed
   writable because `public/` is a bind mount, an undocumented coupling.

## Decision

Move the duration cache out of `PUBLIC_ROOT` into a dedicated, non-served
location, `CACHE_ROOT` (default `/app/.cache`, created on demand; an image
default, not a user setting, see ADR 0004). Keep the on-disk format and
`(path, mtime)` keying. Prune entries whose `path` no longer exists on save.

## Consequences

- Cache is no longer web-reachable regardless of Caddy `hide` config.
- `read_only: true` users mount a small writable volume or tmpfs at
  `CACHE_ROOT` instead of relying on `public/` semantics.
- Backward compatibility: on first run after upgrade, an existing
  `<PUBLIC_ROOT>/.podcastify-cache.json` is read once and migrated, then the
  old file is removed.
- Glossary entry for "Duration cache" must be updated to the new path.

## References

- `MediaProcessor` (`_cache_path`, `_migrate_legacy_cache`, `_save_disk_cache`) in `podcastify/media.py`
- `Config.CACHE_ROOT` and `Config.CACHE_FILENAME` in `podcastify/config.py`
- `docs/deployment.md`

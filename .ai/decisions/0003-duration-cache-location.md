# 0003 - Duration cache location and lifecycle

## Status

Proposed

## Context

`MediaProcessor` persists ffprobe results to
`<PUBLIC_ROOT>/.podcastify-cache.json` (`podcastify/media.py:16-17`,
`Config.CACHE_FILENAME` at `config.py:38`).
`PUBLIC_ROOT` (`/app/public`) is the directory Caddy serves
(`docker/podcastify/Caddyfile:2`). Three problems:

1. The cache file is web-reachable. `hide .*` in the shipped Caddyfile
   (`Caddyfile:19`) returns 404 for direct requests, but the `docs/deployment.md`
   Caddyfile snippet uses `hide .gitkeep`, which would expose it.
2. Cache entries for deleted media are never pruned (`_save_disk_cache`
   serializes the full in-memory dict, `media.py:45-53`), so the file grows
   unbounded.
3. `docs/deployment.md` recommends `read_only: true`; the cache only stays
   writable because `public/` is a bind mount, an undocumented coupling.

## Decision

Move the duration cache out of `PUBLIC_ROOT` into a dedicated, non-served
location controlled by a new `CACHE_ROOT` env var (default `/app/.cache`,
created on demand). Keep the on-disk format and `(path, mtime)` keying.
Prune entries whose `path` no longer exists on save.

## Consequences

- Cache is no longer web-reachable regardless of Caddy `hide` config.
- `read_only: true` users mount a small writable volume or tmpfs at
  `CACHE_ROOT` instead of relying on `public/` semantics.
- Backward compatibility: on first run after upgrade, an existing
  `<PUBLIC_ROOT>/.podcastify-cache.json` is read once and migrated, then the
  old file is removed.
- Glossary entry for "Duration cache" must be updated to the new path.

## References

- `podcastify/media.py:15-63`
- `podcastify/config.py:38`
- `docs/deployment.md:94-108`

# Architecture Notes (AI Agents)

Supplement to `docs/architecture.md` — file:line map, invariants, and gotchas
not covered there. Read both before proposing changes to `podcastify/`.

## Module map

| Module | Class / fn |
|---|---|
| `podcastify/config.py` | `_EnvVar`, `Config`, `_coerce_bool` |
| `podcastify/parser.py` | `EpisodeModel`, `PodcastChannelModel`, `PodcastFileModel` (pydantic) |
| `podcastify/parser.py` | `ConfigurationManager`, `EpisodeManager` |
| `podcastify/logging_config.py` | `configure_logging` |
| `podcastify/media.py` | `MediaProcessor` |
| `podcastify/rss.py` | `RSSGenerator` |
| `podcastify/cli.py` | `PodcastProcessor`, `build_parser`, `main` |

## Invariants & gotchas

- **Env config via descriptor**: `Config` attributes are `_EnvVar` descriptors
  (config.py) — read `os.environ` on every access, not cached at class
  load. Casts applied via the `cast` lambda.
- **Flexible YAML schema**: `PodcastFileModel` accepts a flat config (`podcast:`
  keys at top level) or nested (`podcast:` block) via `accept_flat_or_nested`
  (parser.py). Both forms must keep validating.
- **Legacy `author` field**: `author` maps to `author-name` when `author-name`
  is absent, in `PodcastChannelModel.map_legacy_author` (parser.py).
- **Metadata path**: `PodcastProcessor._build_metadata_from_model` (cli.py)
  builds channel metadata from the validated model, limited to
  `Config.CHANNEL_FIELDS`. `RSSGenerator` still re-defaults some values (for
  example `language` to `en`), so a default changed in `PodcastChannelModel`
  must be changed there too.
- **Episode source priority**: an explicit `episodes:` list (validated via
  pydantic) wins over auto-scanning `public/<name>/` for `Config.MEDIA_TYPES`
  extensions, case-insensitive — `discover_episodes` (parser.py). The same map
  sets the enclosure `type` via `EpisodeManager.media_type`; unknown
  extensions default to `audio/mpeg`.
- **Duration cache**: in-memory `_duration_cache` keyed by `(path, mtime)`,
  persisted to `<CACHE_ROOT>/.podcastify-cache.json` (media.py). A new mtime
  invalidates the entry. On save, only the newest mtime per path is written
  and entries for deleted files are dropped. An ffprobe timeout is cached in
  memory only (`_unpersisted`), so the next run probes the file again; other
  failures are persisted.
- **Duration fallback chain**: episode `duration_hms` (from YAML) →
  `MediaProcessor.get_duration_seconds` via `ffprobe` → omitted entirely if
  ffprobe fails (rss.py).
- **GUID default**: SHA-1 of `<podcast_name>/<filename>`,
  `isPermaLink="false"` (rss.py). Renaming a podcast or episode file
  changes the GUID and breaks subscriber dedup/listen history.
- **Atomic XML write**: feed is written to a hidden tempfile
  (`.<name>.XXXXXXXX.xml.tmp`) in `PUBLIC_ROOT`, flushed and `fsync`ed, then
  `os.replace`'d onto `<name>.xml` (cli.py) — readers never see partial XML,
  and Caddy's `hide .*` never serves the tempfile. At the start of a
  publishing run, `.*.xml.tmp` files older than 10 minutes are removed.
- **Published datetime**: `EpisodeModel.pub_date` is parsed once in the model
  (date, datetime or ISO string; naive values are UTC; invalid values are
  logged and dropped). `EpisodeManager.discover_episodes` stores
  `__published` (`pub_date`, else file mtime in UTC). Sorting (cli.py) and
  `<pubDate>` (rss.py) both read `__published`; newest first.
- **Pipeline**: `PodcastProcessor.process_podcast` (cli.py) — load YAML →
  pydantic validate → extract metadata → require `public/<name>/` to exist →
  discover episodes → warm duration cache in parallel → sort → generate XML →
  atomic write (or skip write if `PUBLISH_XML=false` or `--dry-run`).
- **CLI and exit codes**: `main(argv)` (cli.py) parses with `argparse`:
  `app.py [generate [--dry-run]]`. With `RUN_ON_START=true` the generator
  also runs when no subcommand is given. Exit `0` when every config succeeded
  or none exist, `1` when any config failed, `2` for a usage error (argparse).
  The entrypoint only warns on a non-zero exit.
- **Logging**: modules use `logging.getLogger(__name__)`. `main()` calls
  `configure_logging()` (logging_config.py) once: two handlers on the
  `podcastify` logger (WARNING+ to stderr, below to stdout), level from
  `LOG_LEVEL` read at call time, `propagate=False` so a configured root logger
  does not print every line twice. An unexpected error in `process_podcast`
  is logged with `logger.exception`, so the traceback is kept.

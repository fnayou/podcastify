# Architecture Notes (AI Agents)

Supplement to `docs/architecture.md` — file:line map, invariants, and gotchas
not covered there. Read both before proposing changes to `podcastify/`.

## Module map

| Module | Class / fn | Location |
|---|---|---|
| `podcastify/config.py` | `_EnvVar`, `Config` | config.py, config.py |
| `podcastify/parser.py` | `EpisodeModel`, `PodcastChannelModel`, `PodcastFileModel` (pydantic) | parser.py, parser.py, parser.py |
| `podcastify/parser.py` | `ConfigurationManager` | parser.py |
| `podcastify/parser.py` | `EpisodeManager` | parser.py |
| `podcastify/media.py` | `MediaProcessor` | media.py |
| `podcastify/rss.py` | `RSSGenerator` | rss.py |
| `podcastify/cli.py` | `PodcastProcessor`, `main` | cli.py, cli.py |

## Invariants & gotchas

- **Env config via descriptor**: `Config` attributes are `_EnvVar` descriptors
  (config.py) — read `os.environ` on every access, not cached at class
  load. Casts applied via the `cast` lambda.
- **Flexible YAML schema**: `PodcastFileModel` accepts a flat config (`podcast:`
  keys at top level) or nested (`podcast:` block) via `accept_flat_or_nested`
  (parser.py). Both forms must keep validating.
- **Legacy `author` field**: `author` maps to `author-name` when `author-name`
  is absent, in two places — `map_legacy_author` (parser.py) and
  `extract_podcast_metadata` (parser.py). Keep both in sync.
- **Dual metadata path**: `extract_podcast_metadata` (parser.py) renders
  from a raw-dict whitelist, while pydantic model defaults (e.g. `language="en"`
  in `PodcastChannelModel:64`) are discarded. `RSSGenerator` re-defaults the
  same fields (rss.py) independently. Two sources of truth for the same
  data; both must stay in sync. Stabilization task: render from the validated
  model instead of the raw dict.
- **Episode source priority**: an explicit `episodes:` list (validated via
  pydantic) wins over auto-scanning `public/<name>/*.mp3` —
  `discover_episodes` (parser.py).
- **Duration cache**: in-memory `_duration_cache` keyed by `(path, mtime)`,
  persisted to `<PUBLIC_ROOT>/.podcastify-cache.json` (media.py,38).
  Invalidates on mtime change, but entries for deleted files are never pruned.
- **Duration fallback chain**: episode `duration_hms` (from YAML) →
  `MediaProcessor.get_duration_seconds` via `ffprobe` → omitted entirely if
  ffprobe fails (rss.py).
- **GUID default**: SHA-1 of `<podcast_name>/<filename>`,
  `isPermaLink="false"` (rss.py). Renaming a podcast or episode file
  changes the GUID and breaks subscriber dedup/listen history.
- **Atomic XML write**: feed is written to a tempfile in `PUBLIC_ROOT` then
  `os.replace`'d onto `<name>.xml` (cli.py) — readers never see
  partial XML.
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

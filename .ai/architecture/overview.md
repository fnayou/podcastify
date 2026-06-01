# Architecture Notes (AI Agents)

Supplement to `docs/architecture.md` — file:line map, invariants, and gotchas
not covered there. Read both before proposing changes to `podcastify/`.

## Module map

| Module | Class / fn | Location |
|---|---|---|
| `podcastify/config.py` | `_EnvVar`, `Config` | config.py:6, config.py:19 |
| `podcastify/parser.py` | `EpisodeModel`, `PodcastChannelModel`, `PodcastFileModel` (pydantic) | parser.py:34, parser.py:53, parser.py:89 |
| `podcastify/parser.py` | `ConfigurationManager` | parser.py:115 |
| `podcastify/parser.py` | `EpisodeManager` | parser.py:152 |
| `podcastify/media.py` | `MediaProcessor` | media.py:11 |
| `podcastify/rss.py` | `RSSGenerator` | rss.py:18 |
| `podcastify/cli.py` | `PodcastProcessor`, `main` | cli.py:19, cli.py:142 |

## Invariants & gotchas

- **Env config via descriptor**: `Config` attributes are `_EnvVar` descriptors
  (config.py:6-16) — read `os.environ` on every access, not cached at class
  load. Casts applied via the `cast` lambda.
- **Flexible YAML schema**: `PodcastFileModel` accepts a flat config (`podcast:`
  keys at top level) or nested (`podcast:` block) via `accept_flat_or_nested`
  (parser.py:94-101). Both forms must keep validating.
- **Legacy `author` field**: `author` maps to `author-name` when `author-name`
  is absent, in two places — `map_legacy_author` (parser.py:75-79) and
  `extract_podcast_metadata` (parser.py:129-130). Keep both in sync.
- **Dual metadata path**: `extract_podcast_metadata` (parser.py:126-136) renders
  from a raw-dict whitelist, while pydantic model defaults (e.g. `language="en"`
  in `PodcastChannelModel:64`) are discarded. `RSSGenerator` re-defaults the
  same fields (rss.py:93-104) independently. Two sources of truth for the same
  data; both must stay in sync. Stabilization task: render from the validated
  model instead of the raw dict.
- **Episode source priority**: an explicit `episodes:` list (validated via
  pydantic) wins over auto-scanning `public/<name>/*.mp3` —
  `discover_episodes` (parser.py:154-184).
- **Duration cache**: in-memory `_duration_cache` keyed by `(path, mtime)`,
  persisted to `<PUBLIC_ROOT>/.podcastify-cache.json` (media.py:12-17,38).
  Invalidates on mtime change, but entries for deleted files are never pruned.
- **Duration fallback chain**: episode `duration_hms` (from YAML) →
  `MediaProcessor.get_duration_seconds` via `ffprobe` → omitted entirely if
  ffprobe fails (rss.py:201-204).
- **GUID default**: SHA-1 of `<podcast_name>/<filename>`,
  `isPermaLink="false"` (rss.py:185-188). Renaming a podcast or episode file
  changes the GUID and breaks subscriber dedup/listen history.
- **Atomic XML write**: feed is written to a tempfile in `PUBLIC_ROOT` then
  `os.replace`'d onto `<name>.xml` (cli.py:104-111) — readers never see
  partial XML.
- **Sort order**: episodes sorted by `pub_date` (ISO, `Z` → `+00:00`) else
  file mtime, newest first (cli.py:71-91).
- **Pipeline**: `PodcastProcessor.process_podcast` (cli.py:25) — load YAML →
  pydantic validate → extract metadata → require `public/<name>/` to exist →
  discover episodes → warm duration cache in parallel → sort → generate XML →
  atomic write (or skip write if `PUBLISH_XML=false`).

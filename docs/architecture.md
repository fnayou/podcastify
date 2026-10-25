# Architecture

## Overview

Podcastify is a Python **package** (`podcastify/`) + thin `app.py` entry point. Reads YAML configs, discovers MP3 files, extracts metadata, generates iTunes-compatible RSS feeds. See [deployment](../website/deployment.md) for container runtime.

## Modules and Classes

| Module | Class / fn | Responsibility |
|---|---|---|
| `podcastify/config.py` | `Config`, `_EnvVar` | Env-var descriptors, media types. |
| `podcastify/media.py` | `MediaProcessor` | tinytag duration extraction, persistent cache, iTunes formatting. |
| `podcastify/parser.py` | `ConfigurationManager`, `EpisodeManager`, pydantic models | YAML load + validate, metadata extraction, episode/image discovery. |
| `podcastify/rss.py` | `RSSGenerator` | iTunes-compatible XML feed generation. |
| `podcastify/index.py` | `IndexPage`, `IndexEntry` | Opt-in `index.html` listing the feeds: escaped semantic HTML, generator marker, marker-protected removal. |
| `podcastify/cli.py` | `PodcastProcessor`, `FeedWatcher`, `main` | Orchestration: load → validate → discover → generate → atomic write when the content changed; the index page after the feeds of a run; optional polling watcher that regenerates on config or media changes. |

Note: 8 logical classes (`Config`, `MediaProcessor`, `ConfigurationManager`, `EpisodeManager`, `RSSGenerator`, `IndexPage`, `PodcastProcessor`, `FeedWatcher`) in 6 modules; `ConfigurationManager` + `EpisodeManager` (+ pydantic models + helpers) share `parser.py`, and `PodcastProcessor` + `FeedWatcher` share `cli.py`.

## Data Flow

```
┌─────────────────┐
│  *-podcast.yaml │
└────────┬────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────────┐
│ ConfigurationManager│──▶│  EpisodeManager  │
│   (load + meta)  │     │ (discover MP3s)  │
└────────┬─────────┘     └────────┬────────┘
         │                         │
         └───────────┬─────────────┘
                     ▼
              ┌──────────────┐
              │ RSSGenerator │
              │ (XML output) │
              └──────┬───────┘
                     ▼
              public/<name>.xml
                     │  (PUBLISH_INDEX=true, feeds not `listed: false`)
                     ▼
              ┌──────────────┐
              │  IndexPage   │
              └──────┬───────┘
                     ▼
              public/index.html
```

## Key Behaviors

### Config Discovery

Scans `./podcasts/` for files matching `<name>-podcast.yaml`. The `<name>` prefix (also accepted as `<name>-podcast.yml`) becomes the podcast identifier. It must start with a letter or digit and contain only letters, digits, `.`, `_` and `-`, with no `..`. A config with another name is skipped with a warning. If two configs map to one name, the first in sorted order wins and the other is skipped with an error naming both files.

### Episode Discovery

1. If `episodes:` is present in YAML, use the explicit list.
2. Otherwise, auto-scan `public/<name>/` for `.mp3`, `.m4a`, `.mp4`, `.ogg` and `.opus` files (case-insensitive).
3. Sort by `pub_date` (if present) or file modification time, newest first.

### Duration Extraction

1. If `duration_hms` is set in episode config, use it directly.
2. Otherwise, read the duration of the media file with `tinytag`.
3. Format as `H:MM:SS` or `M:SS` for iTunes compatibility.
4. If `tinytag` fails, or the result is not usable, the `<itunes:duration>` tag is omitted.

A result is not usable when it is not finite, is zero or negative, or is under 1 s for a file of at least 100 KB.

Results are cached in memory by `(path, mtime)` and persisted to `<CACHE_ROOT>/.podcastify-cache.json` (`/app/.cache` in the image, outside the directory Caddy serves). The file holds a format version; entries in any other version are ignored, so every file is read again once. Entries for files that no longer exist are dropped when the cache is saved, and a cache left in `PUBLIC_ROOT` by an older version is migrated on first load. See [ADR 0003](adr/0003-duration-cache-location.md) and [ADR 0006](adr/0006-tinytag-for-durations.md).

### Image Resolution

Images can be:
- A filename (e.g., `cover.jpg`) — resolved from `public/<name>/cover.jpg`
- A full URL (e.g., `https://...`) — used as-is

If the local file doesn't exist, a warning is logged and the tag is omitted.

### GUID Generation

Episode GUIDs default to SHA-1 of `<podcast-name>/<filename>` and are marked with `isPermaLink="false"`. Custom GUIDs can be set per episode.

### XML Generation

The generated RSS includes:
- Standard RSS 2.0 tags (`title`, `link`, `description`, `language`, `lastBuildDate`) and `atom:link rel="self"` pointing at `PUBLIC_BASE_URL/<name>.xml`
- iTunes channel tags (`itunes:author`, `itunes:owner`, `itunes:image`, `itunes:category`, `itunes:explicit`)
- iTunes item tags (`itunes:duration`, `itunes:episode`, `itunes:season`, `itunes:episodeType`, `itunes:explicit`)

The root element declares the `itunes`, `content` and `atom` namespaces. `itunes:explicit` is written as `true` or `false`.

The feed is built as an `xml.etree.ElementTree` tree from the validated models, so all text and attributes are escaped by the standard library; characters XML does not allow are removed. Optional tags whose text is empty or blank (such as `description`, `itunes:author` and `itunes:summary`) are left out of the feed.

# Architecture

## Overview

Podcastify is a Python **package** (`podcastify/`) + thin `app.py` entry point. Reads YAML configs, discovers MP3 files, extracts metadata, generates iTunes-compatible RSS feeds. See [deployment](deployment.md) for container runtime.

## Modules and Classes

| Module | Class / fn | Responsibility |
|---|---|---|
| `podcastify/config.py` | `Config`, `_EnvVar` | Env-var descriptors, field whitelists. |
| `podcastify/media.py` | `MediaProcessor` | ffprobe duration extraction, persistent cache, iTunes formatting. |
| `podcastify/parser.py` | `ConfigurationManager`, `EpisodeManager`, pydantic models | YAML load + validate, metadata extraction, episode/image discovery. |
| `podcastify/rss.py` | `RSSGenerator` | iTunes-compatible XML feed generation. |
| `podcastify/cli.py` | `PodcastProcessor`, `main` | Orchestration: load → validate → discover → generate → atomic write. |

Note: 6 logical classes in 5 modules; `ConfigurationManager` + `EpisodeManager` (+ pydantic models + helpers) share `parser.py`.

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
```

## Key Behaviors

### Config Discovery

Scans `./podcasts/` for files matching `<name>-podcast.yaml`. The `<name>` prefix becomes the podcast identifier.

### Episode Discovery

1. If `episodes:` is present in YAML, use the explicit list.
2. Otherwise, auto-scan `public/<name>/` for `*.mp3` files.
3. Sort by `pub_date` (if present) or file modification time, newest first.

### Duration Extraction

1. If `duration_hms` is set in episode config, use it directly.
2. Otherwise, run `ffprobe -show_entries format=duration` on the MP3.
3. Format as `H:MM:SS` or `M:SS` for iTunes compatibility.
4. If ffprobe fails, the `<itunes:duration>` tag is omitted.

### Image Resolution

Images can be:
- A filename (e.g., `cover.jpg`) — resolved from `public/<name>/cover.jpg`
- A full URL (e.g., `https://...`) — used as-is

If the local file doesn't exist, a warning is logged and the tag is omitted.

### GUID Generation

Episode GUIDs default to SHA-1 of `<podcast-name>/<filename>` and are marked with `isPermaLink="false"`. Custom GUIDs can be set per episode.

### XML Generation

The generated RSS includes:
- Standard RSS 2.0 tags (`title`, `link`, `description`, `language`, `lastBuildDate`)
- iTunes channel tags (`itunes:author`, `itunes:owner`, `itunes:image`, `itunes:category`, `itunes:explicit`)
- iTunes item tags (`itunes:duration`, `itunes:episode`, `itunes:season`, `itunes:episodeType`)

Empty values produce empty tags rather than CDATA blocks with whitespace.

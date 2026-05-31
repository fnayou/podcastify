# Architecture

## Overview

Podcastify is a single-file Python application (`app.py`) with a class-based architecture. It reads YAML configs, discovers MP3 files, extracts metadata, and generates iTunes-compatible RSS XML feeds.

## Classes

| Class | Responsibility |
|---|---|
| `Config` | Centralized constants and environment variables. |
| `MediaProcessor` | `ffprobe` duration extraction and iTunes duration formatting. |
| `ConfigurationManager` | YAML loading, metadata extraction, podcast config discovery. |
| `EpisodeManager` | Episode discovery (explicit list or auto-scan), image URL resolution. |
| `RSSGenerator` | iTunes-compatible XML feed generation with all channel/episode tags. |
| `PodcastProcessor` | Orchestrator: load configs → discover episodes → generate feeds. |

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

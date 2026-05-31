# Configuration

## Overview

Podcastify reads one YAML file per podcast from `./podcasts/`. The filename must end with `-podcast.yaml` or `-podcast.yml` (e.g., `myshow-podcast.yaml`). The name before the suffix becomes the podcast identifier used in URLs and feed filenames.

## Minimal Example

```yaml
name: "myshow"
title: "My Private Show"
author-name: "Your Name"
author-email: "you@example.com"
description: "Personal feed for testing"
language: "en"
explicit: false
image: "cover.jpg"
categories:
  - "Technology"
```

## Channel Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | No | Podcast identifier. If omitted, derived from the filename. |
| `title` | string | Yes | Podcast title shown in podcast apps. |
| `author-name` | string | Yes | Author/creator name. |
| `author-email` | string | No | Contact email for the podcast owner. |
| `description` | string | Yes | Short description of the podcast. |
| `subtitle` | string | No | Brief subtitle for display in podcast apps. |
| `summary` | string | No | Longer summary. Falls back to `description` if omitted. |
| `language` | string | No | Language code (e.g., `en`, `fr`). Defaults to `en`. |
| `explicit` | boolean | No | Whether content is explicit. Defaults to `false`. |
| `image` | string | No | Cover image filename (in `public/<name>/`) or full URL. |
| `link` | string | No | Website URL for the podcast. Defaults to `PUBLIC_BASE_URL`. |
| `categories` | array | No | iTunes categories. See formats below. |
| `type` | string | No | `episodic` or `serial`. |
| `block` | boolean | No | If `true`, prevents the podcast from appearing in iTunes. |
| `complete` | boolean | No | If `true`, marks the podcast as complete (no new episodes). |
| `new_feed_url` | string | No | Redirect URL for subscribers if the feed moves. |

## Categories Format

Categories support flexible input:

```yaml
# Single category
categories: "Technology"

# Multiple categories
categories:
  - "Technology"
  - "Education"

# With subcategories (array of arrays)
categories:
  - ["Society & Culture", "Personal Journals"]
  - ["Technology", "Software How-To"]

# With subcategories (dictionary style)
categories:
  - name: "Society & Culture"
    sub: "Personal Journals"
  - name: "Technology"
    sub: "Software How-To"
```

## Episodes

If you omit the `episodes:` list, Podcastify auto-discovers all `*.mp3` files in `public/<name>/`, sorted by modification time (newest first).

### Explicit Episode List

```yaml
episodes:
  - file: "ep01.mp3"
    title: "Hello World"
    description: "First episode"
    pub_date: "2025-01-01T08:00:00Z"
    image: "episode.png"
    explicit: false
    season: 1
    episode: 1
    episode_type: "full"
    guid: "custom-guid-if-you-really-want"
```

### Episode Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | string | Yes | MP3 filename (basename only, placed in `public/<name>/`). |
| `title` | string | No | Episode title. Defaults to the filename stem. |
| `description` | string | No | Episode description. |
| `summary` | string | No | Longer summary. Falls back to `description`. |
| `subtitle` | string | No | Brief subtitle. |
| `pub_date` | string | No | ISO 8601 datetime. Defaults to file modification time. |
| `image` | string | No | Episode image filename or URL. |
| `explicit` | boolean | No | Overrides channel `explicit` if set. |
| `author-name` | string | No | Overrides channel author for this episode. |
| `season` | integer | No | Season number. |
| `episode` | integer | No | Episode number within season. |
| `episode_type` | string | No | `full`, `trailer`, or `bonus`. |
| `guid` | string | No | Unique identifier. Defaults to SHA-1 of `<podcast>/<filename>`. |
| `duration_hms` | string | No | Pre-set duration as `H:MM:SS` or `M:SS`. If omitted, extracted via `ffprobe`. |

## File Placement

```
podcasts/
  myshow-podcast.yaml

public/
  myshow/
    ep01.mp3
    cover.jpg
    episode.png
  myshow.xml          # Generated feed
```

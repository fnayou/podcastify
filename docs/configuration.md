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

## Fields

The tables below are generated from the models in `podcastify/parser.py`; do not edit them by hand. See [Contributing](contributing.md#configuration-reference).

<!-- BEGIN GENERATED: fields -->

### Channel Fields

| Key | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | string | No | - | Optional; the name before `-podcast.yaml` is always the identifier, and a different `name` is ignored with a warning |
| `title` | string | Yes | - | Podcast title shown in podcast apps |
| `author-name` | string | No | - | Author or creator name; with neither this nor `author`, the feed has no author element |
| `author` | string | No | - | **Deprecated**, use `author-name`. Legacy alias, used as the author name when `author-name` is absent or empty |
| `author-email` | string | No | - | Contact email for the podcast owner |
| `subtitle` | string | No | - | Brief subtitle shown in podcast apps |
| `summary` | string | No | - | Longer summary; falls back to `description` when omitted |
| `description` | string | Yes | - | Short description of the podcast |
| `language` | string | No | `en` | Language code, for example `en` or `fr` |
| `explicit` | boolean | No | `false` | Whether the content is explicit |
| `image` | string | No | - | Cover image filename in `public/<name>/`, or a full URL |
| `link` | string | No | - | Website URL for the podcast; defaults to `PUBLIC_BASE_URL` |
| `categories` | string, list or mapping | No | - | iTunes categories; see [Categories Format](#categories-format) |
| `type` | string | No | - | `episodic` or `serial` |
| `block` | boolean | No | - | If `true`, prevents the podcast from appearing in iTunes |
| `complete` | boolean | No | - | If `true`, marks the podcast as complete (no new episodes) |
| `new_feed_url` | string | No | - | Redirect URL for subscribers if the feed moves |
| `listed` | boolean | No | `true` | List this feed on the generated index page; false hides it from the page only, not from its URL |
| `episodes` | list of episode | No | - | Explicit episode list; a non-empty list turns auto-discovery off, see [Episodes](#episodes) |

### Episode Fields

| Key | Type | Required | Default | Description |
|---|---|---|---|---|
| `file` | string | Yes | - | Media filename (`.mp3`, `.m4a`, `.mp4`, `.ogg` or `.opus`), basename only, placed in `public/<name>/`; empty, `.` and `..` are rejected, and so is a second entry with the same basename |
| `title` | string | No | - | Episode title; defaults to the filename stem |
| `description` | string | No | - | Episode description |
| `summary` | string | No | - | Longer summary; falls back to `description` |
| `subtitle` | string | No | - | Brief subtitle |
| `pub_date` | date-time | No | - | ISO 8601 date or date-time, quoted or not; a value without a timezone is read as UTC, an invalid value is logged and ignored; defaults to the file modification time |
| `image` | string | No | - | Episode image filename or URL |
| `explicit` | boolean | No | - | Overrides the channel `explicit` when set |
| `author-name` | string | No | - | Overrides the channel author for this episode |
| `season` | integer | No | - | Season number |
| `episode` | integer | No | - | Episode number within the season |
| `episode_type` | string | No | - | `full`, `trailer` or `bonus` |
| `guid` | string | No | - | Unique identifier; defaults to the SHA-1 of `<podcast>/<filename>`; must be unique within the podcast, a duplicate rejects the whole config |
| `duration_hms` | string | No | - | Pre-set duration as `H:MM:SS` or `M:SS`; read from the media file with `tinytag` when omitted |

<!-- END GENERATED -->

A key that is not listed in these tables is ignored, and a warning names it, for example `Unknown config key 'episodes[2].pubdate' ignored; check its spelling`. The config is still published.

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

If you omit the `episodes:` list, Podcastify auto-discovers all `.mp3`, `.m4a`, `.mp4`, `.ogg` and `.opus` files in `public/<name>/`, matched case-insensitively (`EP01.MP3` is found), sorted by modification time (newest first).

A non-empty `episodes:` list turns auto-discovery off: only the listed files are published, and other files in `public/<name>/` are ignored until you add them to the list. An empty list (`episodes: []`) keeps discovery on.

Each enclosure carries the MIME type of its extension: `audio/mpeg` (`.mp3`), `audio/x-m4a` (`.m4a`), `video/mp4` (`.mp4`), `audio/ogg` (`.ogg`) and `audio/opus` (`.opus`). Any other extension named in `episodes:` is published as `audio/mpeg`.

Set `pub_date` on every episode for a stable feed. The modification time changes when files are copied, restored from a backup or moved to another host, which reorders episodes and gives them new `pubDate` values, so some podcast apps show them as new.

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

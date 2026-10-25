# How it works

## The feed pipeline

```
podcasts/<name>-podcast.yaml ─┐
                              ├─▶ validate ─▶ discover episodes ─▶ read durations ─▶ public/<name>.xml
public/<name>/ (media)  ──────┘                                                         │
                                                      (PUBLISH_INDEX=true)              ▼
                                                                                 public/index.html
```

1. The generator reads every `podcasts/<name>-podcast.yaml` (or `.yml`). The `<name>` part becomes the podcast
   identifier and the feed file name. A config with an invalid name is skipped with a warning; if two configs give the
   same name, the first in sorted order wins.
2. Without an `episodes:` list, it scans `public/<name>/` for `.mp3`, `.m4a`, `.mp4`, `.ogg` and `.opus` files, newest
   first. With a list, only the listed files are published.
3. It reads each duration with `tinytag`, or uses `duration_hms` when you set it. A duration that cannot be read is
   left out of the feed.
4. It writes `public/<name>.xml`. The feed is built from validated data, so all text is escaped, and the file is
   rewritten only when its content changes (a new `<lastBuildDate>` alone does not count), so podcast apps do not
   refetch an unchanged feed.
5. With `PUBLISH_INDEX=true`, it also writes `public/index.html`, which lists the feeds that are not `listed: false`.

Episode GUIDs default to the SHA-1 of `<podcast>/<filename>`. Renaming a file therefore creates a new episode for
subscribers; set `guid:` on the episode to keep the old one.

Measured durations are cached in `/app/.cache/.podcastify-cache.json`, keyed by path and modification time. Keep that
folder on a volume so a restart does not read every file again.

## The image

One container runs Caddy in the foreground under `tini`. Caddy serves `/app/public` (feeds, media and the optional
index) on `SERVICE_PORT`. The generator runs once at boot when `RUN_ON_START` is true, and on demand with
`docker exec podcastify /entrypoint.sh generate`.

| Path in the container | Content |
|---|---|
| `/app/podcasts` | your `<name>-podcast.yaml` files (read) |
| `/app/public` | media, generated feeds and index (served) |
| `/app/.cache` | duration cache and Caddy's own data |

### Automatic regeneration

With `GENERATE_INTERVAL` set to a number of seconds above `0`, a background watcher compares the configs and media
(path, size, modification time) every interval and regenerates the feeds when something changed. It polls, so it works
on network shares and Docker Desktop mounts, where file events do not arrive. `0`, the default, turns it off.

### User and permissions

By default the container starts as root, gives the files it writes (the cache, `public/` and the feeds) to
`PUID`/`PGID` (default `1000`), and then drops to that user. Your media and configs keep their owner and only need to be
readable by it. For a hardened setup, pin the container `user:` instead; the entrypoint then changes no owner, so the
mounted folders must already belong to that user. See [Security hardening](deployment.md#security-hardening).

### Healthcheck

The image checks `/healthz`, a fixed `200 ok` that Caddy does not log, every 30 seconds, with a 120 second start period
for the first generation on a large library.

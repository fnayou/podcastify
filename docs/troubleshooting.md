# Troubleshooting

## Common Issues

Each log line reads `<time> <LEVEL> <logger>: <message>`. Search the message text below in `task docker:logs`; warnings and errors are written to stderr.

### "No podcast configurations found"

**Cause:** No `*-podcast.yaml` files in `./podcasts/`

**Fix:**
- Create a config: `task podcastify:new NAME=myshow`
- Ensure the filename ends with `-podcast.yaml`

### "Public directory missing for <name>"

**Symptom:** `WARNING podcastify.cli: Public directory missing for myshow: /app/public/myshow`, followed by `Create directory and place MP3 files there`. No feed is written for this podcast.

**Cause:** There is no `public/<name>/` folder for that config.

**Fix:**
```bash
mkdir -p public/myshow
cp /path/to/*.mp3 public/myshow/
```

### "No episodes found for <name>"

**Symptom:** `WARNING podcastify.cli: No episodes found for myshow in /app/public/myshow`

**Cause:** `public/<name>/` exists but holds no `.mp3`, `.m4a`, `.mp4`, `.ogg` or `.opus` file, or every file named in `episodes:` is missing.

**Fix:** Copy media into `public/<name>/`, then run `task podcastify:generate`.

### "Skipping episode for <name>: file not found"

**Symptom:** `WARNING podcastify.cli: Skipping episode for myshow: file not found: ep01.mp3`. The other episodes are still published, and the summary line reads `Published myshow: N episodes (K skipped)`

**Cause:** The `episodes:` list names a file that doesn't exist in `public/<name>/`.

**Fix:** Check the `file:` field in your YAML matches the actual filename, including case and extension (basename only, no subdirectories). Remember that a non-empty `episodes:` list turns auto-discovery off.

### "Empty or invalid config for <name>"

**Symptom:** `ERROR podcastify.cli: Empty or invalid config for myshow`, often preceded by `ERROR podcastify.parser: Failed to load config <path>: ...`.

**Cause:** The YAML file is empty, has a syntax error or cannot be read.

**Fix:** Open `podcasts/<name>-podcast.yaml` and fix the YAML syntax; the text after `Failed to load config <path>:` names the problem.

### "Config validation failed for <name>"

**Symptom:** `ERROR podcastify.cli: Config validation failed for myshow: ...`, for example `type must be 'episodic' or 'serial'` or a missing `title` or `description`.

**Cause:** The config does not match the [configuration reference](configuration.md): a required field is missing, a value has the wrong type, `episodes` repeats a file or `guid`, or the file is not a mapping.

**Fix:** Correct the field the message names. The feed for this podcast is not written until it validates.

### "Unknown config key ... ignored"

**Symptom:** `WARNING podcastify.parser: Unknown config key 'titel' ignored; check its spelling`. Episode keys appear as `episodes[2].pubdate`.

**Cause:** The key is not a known channel or episode field, so it has no effect. The feed is still published.

**Fix:** Fix the spelling against the [configuration reference](configuration.md).

### "Image file not found"

**Symptom:** `WARNING podcastify.parser: Image file not found: /app/public/myshow/cover.jpg`. The feed is published without that image.

**Cause:** `image:` names a file that is not in `public/<name>/`. Only the filename is used; any directory part is dropped.

**Fix:** Copy the image into `public/<name>/`, or use a full `https://` URL.

### ffprobe duration extraction fails

**Symptom:** `WARNING podcastify.media: Failed to get duration for ep01.mp3: <reason>`, or once per run `ffprobe not found; publishing feeds without episode durations`.

**Cause:** `ffprobe` is not available inside the container, or the MP3 is corrupted.

**Fix:**
- The container image includes `ffprobe`. If building locally, ensure ffmpeg is installed.
- If extraction fails, the episode will still generate but without `<itunes:duration>`.
- You can manually set `duration_hms` in the episode config as a workaround.

### "Could not chown ...; continuing"

**Symptom:** In `docker compose logs`, before the generator starts: `Could not chown /app/public; continuing (check bind-mount perms)`, preceded by chown's own error line. The same message can name `/app/.cache` or a `public/*.xml` feed.

**Cause:** The container starts as root and tries to give `.cache/`, `public/` and the feeds to `PUID`/`PGID`, but the host mount refuses the change (NFS or SMB share, root squash, or `cap_drop: ALL`). The container keeps starting.

**Fix:** Set `PUID` and `PGID` in `.env` to the uid and gid that already own the mounted folders, so no chown is needed. See [Permissions](#permissions).

### "Generator exited non-zero; continuing to serve existing content"

**Symptom:** The container log shows `Generator exited non-zero; continuing to serve existing content` after `Running generator at startup...`.

**Cause:** At least one podcast failed during the startup run, so the generator exited with status 1. Caddy still starts and serves the feeds already on disk. The log ends the run with `Generator finished: N podcast(s) failed`.

**Fix:** Read the `ERROR` and `WARNING` lines above it (see the entries above) and fix the config or files. Then run `task podcastify:generate`, or set `GENERATE_INTERVAL` so a failed run is retried on the next change.

### Port already in use

**Symptom:** `bind: address already in use`

**Fix:** Change `HOST_PORT` in `.env`:
```env
HOST_PORT=8081
```

### Feed not updating

**Cause:** Generator not running, or `PUBLISH_XML=false`.

**Fix:**
```bash
# Check container status
task docker:status

# Force regenerate
task podcastify:generate

# Check env vars
cat .env | grep PUBLISH_XML
```

## Permissions

The generator must be able to write `public/` (feeds), `.cache/` (duration cache) and read `podcasts/` and the media. In the default start the container runs as root, gives `.cache/`, `public/` and `public/*.xml` to `PUID`/`PGID` (default `1000`), and runs the generator and Caddy as that user. Media and configs keep their host owner, so they only need to be readable by that uid.

- Set `PUID` and `PGID` in `.env` to the owner of your mounted folders (`id -u`, `id -g`), then restart: `task docker:restart`.
- On a Linux host you can fix ownership with `task docker:fix:perms UID=$(id -u) GID=$(id -g)`.
- If you pin the container user (`user:` in compose, hardened mode), the entrypoint skips chown, so the mounts must already belong to that uid. See [Deployment](deployment.md#security-hardening) and [runtime](runtime.md#non-root-via-puidpgid).
- A write failure shows up as `ERROR podcastify.cli: Failed to process <name>: [Errno 13] Permission denied: ...` with a traceback.

## Log Inspection

```bash
# Follow logs
task docker:logs

# Recent logs only
task docker:logs:recent

# Errors only
task docker:logs:errors

# Shell into container
task docker:shell
```

### Enable Debug Logging

To increase verbosity and see detailed trace information (config discovery, episode probing, cache operations, ffprobe invocations):

```bash
# At boot
LOG_LEVEL=DEBUG docker compose up

# On-demand generate
docker compose exec -e LOG_LEVEL=DEBUG podcastify /entrypoint.sh generate

# Or in .env
LOG_LEVEL=DEBUG
docker compose up
```

Valid levels are `DEBUG`, `INFO` (default), `WARNING`, and `ERROR`. Debug output appears in `docker compose logs` and is useful for verifying the app is working correctly.

## Task Doctor

Run `task doctor` for a quick environment check.

## Still Stuck?

- Check [GitHub Issues](https://github.com/fnayou/podcastify/issues)
- Review [Configuration reference](configuration.md)
- Review [Deployment guide](deployment.md)

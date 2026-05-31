# Troubleshooting

## Common Issues

### "No podcast configurations found"

**Cause:** No `*-podcast.yaml` files in `./podcasts/`

**Fix:**
- Create a config: `task podcastify:new NAME=myshow`
- Ensure the filename ends with `-podcast.yaml`

### "No episodes found for <name>"

**Cause:** `public/<name>/` directory is missing or empty.

**Fix:**
```bash
mkdir -p public/myshow
cp /path/to/*.mp3 public/myshow/
```

### "Missing episode files"

**Cause:** Config references a file that doesn't exist in `public/<name>/`.

**Fix:** Check the `file:` field in your YAML matches the actual MP3 filename (basename only, no subdirectories).

### ffprobe duration extraction fails

**Symptom:** `[WARN] Failed to get duration for ...`

**Cause:** `ffprobe` is not available inside the container, or the MP3 is corrupted.

**Fix:**
- The container image includes `ffprobe`. If building locally, ensure ffmpeg is installed.
- If extraction fails, the episode will still generate but without `<itunes:duration>`.
- You can manually set `duration_hms` in the episode config as a workaround.

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

## Task Doctor

Run `task doctor` for a quick environment check.

## Still Stuck?

- Check [GitHub Issues](https://github.com/fnayou/podcastify/issues)
- Review [Configuration reference](configuration.md)
- Review [Deployment guide](deployment.md)

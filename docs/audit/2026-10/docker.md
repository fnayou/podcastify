# Podcastify audit: DOCKER

Scope: `docker/podcastify/Dockerfile`, `docker/podcastify/Caddyfile`, `docker/podcastify/entrypoint.sh`, `docker-compose.yml`, `.dockerignore`, `.env.example`, `docs/runtime.md`, `docs/deployment.md`, `docs/adr/`. I also read the code and files these depend on (`podcastify/config.py`, `podcastify/media.py`, `podcastify/cli.py`, `tasks/*.yml`, `README.md`, the workflows) to check the contract. Branch `main` at `963a220`. Nothing was built or run. Every claim below comes from reading the files, plus the official Caddy and Alpine package pages where noted.

---

### DOCKER-01 README hardening snippet crash-loops the default image; README still teaches retired `PORT`
- severity: high
- evidence:
  - `README.md:182-187` recommends `read_only: true`, `cap_drop: ["ALL"]` with no `user:` line: "The image runs fine as-is. For additional defense-in-depth, you can apply these Compose settings".
  - `README.md:190`: "drop Linux capabilities (the app listens on high port `${PORT}` so none are needed)".
  - `entrypoint.sh:17-22`: when started as root it runs `chown -R` and then `RUNAS="su-exec ${PUID}:${PGID}"`; `entrypoint.sh:16` itself says this "needs CHOWN/SETUID/SETGID caps".
  - `README.md:128` `PORT=8080`, `README.md:154` `:{$PORT} {`, `README.md:161` `hide .gitkeep`, `README.md:192-197` "`v1.0.1+` ... `user: "10001:10001"`".
- problem: The README is the landing page, and it is mirrored to Docker Hub. A user who copies its hardening block without `user:` starts the container as root with no capabilities. The chown fails, but its error is swallowed (`2>/dev/null`). Then `su-exec` cannot call setgroups/setgid, so the generator fails. The final `exec /sbin/tini -- su-exec ... caddy` fails too, the container exits, and `restart: unless-stopped` loops it. `docs/deployment.md:123` already warns about exactly this; the README contradicts it. The README also still documents `PORT`, which ADR 0002 retired ("`PORT` is retired"). The shipped Caddyfile binds `{$SERVICE_PORT}`, so setting `PORT` does nothing. Its Caddyfile example (`hide .gitkeep`) is the variant ADR 0003 calls out because it would expose dotfiles. The `10001:10001` uid hint is invented: no published image uses that uid.
- fix: Replace the README's env, Caddyfile and hardening sections with short pointers to `docs/deployment.md`, which is accurate. If they stay inline, copy the deployment.md hardening block (with `user: "1000:1000"`) and the two-mode explanation. Drop `PORT` everywhere except a one-line migration note.
- effort: S
- depends-on: none

### DOCKER-02 `browse` publishes a full index of every feed and media file
- severity: high
- evidence:
  - `Caddyfile:17-20`: `file_server {` / `browse` / `hide .*` / `}`.
  - `release.yml:92` describes the image as: "Create private podcast feeds from your own MP3s".
  - `docs/runtime.md:59` healthcheck hits `/`, which only returns 200 because of `browse`.
- problem: The product promise is private feeds, and in practice the only privacy is that nobody knows the URL. With `browse`, anyone who reaches the host gets a listing at `/` of every `<name>.xml` and every `/<name>/` media folder. The listing comes as HTML, JSON or plaintext, depending on the `Accept` header (Caddy `file_server` docs). Feed readers and podcast apps never need directory listings. Caddy's docs also state that `hide` "is not a security boundary".
- fix: Remove `browse`. Requests to `/` and to folders then return 404, so the healthcheck must move to a dedicated path at the same time (see DOCKER-10). If some owners want a listing, add an opt-in env such as `BROWSE=true`. Rendering that option needs either two Caddyfiles or an `import` snippet, so the default-off removal is the simple part.
- effort: S
- depends-on: DOCKER-10 (ship together)

### DOCKER-03 Entrypoint recursively chowns all media and configs on every boot
- severity: medium
- evidence: `entrypoint.sh:20`: `chown -R "${PUID}:${PGID}" /app/.cache /app/public /app/podcasts 2>/dev/null \`
- problem: The generator never writes inside `public/<name>/` or `podcasts/`. It only reads them. It writes `public/<name>.xml` plus a `mkstemp` temp file in `public/` (`cli.py:125-134`) and the cache under `CACHE_ROOT` (`media.py:76-92`). Even so, every root-mode boot walks the whole media tree. That costs:
  - Startup time. On a NAS or network mount with thousands of episodes, every inode gets a chown and a ctime update, on every restart.
  - Host ownership changes. On the host, the user's media and configs get re-owned to `PUID:PGID`. That can break other services sharing the folder, for example a media server or a sync tool running as another user.
  - Silent failure. On NFS with `root_squash`, the chown fails, the error is hidden by `2>/dev/null`, and only a vague warning is printed.
- fix: Chown only what the app writes: the top-level `public/` directory (not `-R`), existing `public/*.xml`, and `-R` on the cache dir. Leave `podcasts/` and media untouched. Skip the chown when ownership already matches (`[ "$(stat -c %u:%g "$d")" = "${PUID}:${PGID}" ]`). Drop `2>/dev/null` so the real error is visible.
- effort: S
- depends-on: DOCKER-06 (use the env-driven paths)

### DOCKER-04 On-demand generation runs as root and leaves root-owned files on the host
- severity: medium
- evidence:
  - `tasks/podcastify.yml:18`: `{{.COMPOSE}} exec {{.SERVICE_NAME}} python {{.APP_SCRIPT}} generate`
  - `tasks/podcastify.yml:21`: `{{.COMPOSE}} run --rm --entrypoint '' {{.SERVICE_NAME}} python {{.APP_SCRIPT}} generate`
  - The Dockerfile has no `USER`, so in default mode `exec` and `run` start as uid 0.
- problem: PUID/PGID exists so that generated files are not written as root (`Dockerfile:40-42`). But both documented ways to regenerate without a restart skip the entrypoint's `su-exec` drop. `exec` runs as root, and `run --entrypoint ''` runs as root without the entrypoint at all. Either way, `public/<name>.xml` and `cache/.podcastify-cache.json` come out root-owned on the host. In default mode the next boot's chown hides the damage. In hardened mode (`user:` pinned) `exec` behaves correctly, but `run --entrypoint ''` still runs as root, unless the compose `user:` override applies. It does for `run`, so this mostly bites the default mode. `docs/deployment.md:84` documents the same `exec` command for end users.
- fix: Give the entrypoint a pass-through mode: `entrypoint.sh generate` runs the generator under the same `$RUNAS` logic, then exits. Make the tasks and docs call `docker compose exec podcastify /entrypoint.sh generate`, or drop the `--entrypoint ''` override for `run`. The smallest alternative is `exec --user "${PUID}:${PGID}"`.
- effort: S
- depends-on: DOCKER-05 (if a watcher lands, on-demand generation becomes rare)

### DOCKER-05 Feeds go stale: generator runs only at boot, and the watch tasks are host-only
- severity: medium
- evidence:
  - `entrypoint.sh:28-33` runs the generator once before Caddy. `docs/runtime.md:27` says: "the generator runs once at boot".
  - `docs/deployment.md:87`: "re-run the generator at boot by restarting the container".
  - The only automation is `tasks/podcastify.yml:37-67`, which loops `inotifywait` on the host and needs Taskfile, `inotify-tools` and Linux.
  - `rss.py:113` writes a fresh `<lastBuildDate>` on every run.
- problem: The pitch is "drop MP3s into a folder". For a Docker Hub user, though, a new episode only appears after a container restart or a manual exec. Nothing tells them that. The Taskfile watchers are contributor tooling: they do not exist for image users, and inotify does not fire reliably on SMB/NFS or Docker Desktop bind mounts anyway.
- fix: Add a lightweight in-container rerun with no new dependencies. Options:
  - (a) A `GENERATE_INTERVAL` env, default `0` meaning off. When set, the entrypoint backgrounds `python app.py watch --interval N`. That stdlib loop compares a cheap fingerprint (paths, sizes, mtimes of `podcasts/*.yaml` and `public/*/*.mp3`) and regenerates only on change.
  - (b) Document `docker compose exec ... generate` from host cron as the supported path.

  Prefer (a), and pair it with writing the XML only when its content changes, ignoring `lastBuildDate`. Otherwise every tick rewrites the feed and makes clients refetch. Option (a) makes Caddy no longer the sole process, so tini must be real PID 1 for the whole container life (DOCKER-09). Avoid adding supervisord back or an inotify dependency.
- effort: M
- depends-on: DOCKER-09

### DOCKER-06 Path env vars are advertised but only half honoured
- severity: medium
- evidence:
  - `config.py:20-22` reads `PODCASTS_ROOT`, `PUBLIC_ROOT` and `CACHE_ROOT` from the environment.
  - `docker-compose.yml:15-17`, `.env.example:9-11` and `docs/deployment.md:67-69` expose them as settings.
  - `Caddyfile:2` hardcodes `root * /app/public`.
  - `entrypoint.sh:19-20` hardcodes `/app/public /app/podcasts /app/.cache`.
  - `Dockerfile:56-57` hardcodes `XDG_DATA_HOME=/app/.cache/caddy`.
- problem: If a user sets `PUBLIC_ROOT=/data/public`, the generator writes feeds there. Caddy keeps serving `/app/public` and the entrypoint chowns the wrong dirs, so feeds silently never appear. `CACHE_ROOT` changes have the same problem with chown and the Caddy XDG location. The `.env.example` comment ("don't change unless you know why") admits the trap rather than fixing it.
- fix: Choose one of two:
  - (a) Remove these three from compose, `.env.example` and the deployment table. Keep them as internal Dockerfile defaults, and change mount points through volumes instead. This is simplest and recommended.
  - (b) Honour them everywhere: `root * {$PUBLIC_ROOT}` in the Caddyfile, `"${PUBLIC_ROOT}"` and friends in the entrypoint, and XDG paths derived from `CACHE_ROOT` in the entrypoint.
- effort: S
- depends-on: none

### DOCKER-07 Full ffmpeg stack installed only to read MP3 durations
- severity: medium
- evidence:
  - `Dockerfile:11-12`: `apk add --no-cache \ ffmpeg \`.
  - The only use is `ffprobe` in `media.py:114-121`.
  - Alpine 3.22 `ffmpeg` 6.1.2-r2 depends on `libavcodec`, `libavdevice`, `libavfilter`, `libavformat`, `libavutil`, `libpostproc`, `libswresample` and `libswscale` (pkgs.alpinelinux.org). Alpine ships no standalone `ffprobe` package; `ffmpeg` "provides cmd:ffprobe".
- problem: The libav* libraries pull in the codec and filter libraries (video encoders and decoders included). Measure it with `docker image history`, but this is very likely the bulk of the image and of the CVE surface that Trivy and Scout keep flagging (see `c445816 fix(docker): patch image vulnerabilities`). The project only needs duration and size for MP3, which the enclosures are hardcoded to (`parser.py:181` `glob("*.mp3")`, `rss.py:221` `type="audio/mpeg"`). Because the probe runs out-of-process, it also needs thread pools, timeouts, stderr parsing and a stream fallback (`media.py:114-208`).
- fix: Replace ffprobe with a small pure-Python reader. `tinytag` is MIT-licensed with no dependencies and reads MP3 duration, including Xing/VBRI VBR headers. `mutagen` is more mature, but it is GPL-2.0, which does not fit an MIT project. Then drop `ffmpeg` from the image and from CI's `apt-get install ffmpeg`. Keep the duration cache, because it still saves reads on large libraries. Validate durations against ffprobe on a sample of real episodes before switching.
- effort: M
- depends-on: none (it makes DOCKER-08 moot)

### DOCKER-08 Missing ffprobe aborts the whole podcast instead of degrading
- severity: low
- evidence:
  - `media.py:172-181` catches only `CalledProcessError`, `TimeoutExpired` and `ValueError`. `subprocess.run([...ffprobe...])` raises `FileNotFoundError` when the binary is absent.
  - `media.py:234-235`: `for future in as_completed(futures): future.result()` re-raises in the caller.
  - `cli.py:147-149`: `except Exception as e: logger.error(f"Failed to process {podcast_name}: {e}")`.
- problem: When run outside the image (local `python app.py`, a slim custom image), the missing binary propagates out of `warm_durations_parallel`. Every podcast then fails with "Failed to process X: [Errno 2] No such file or directory: 'ffprobe'" and no feed gets written, though duration is optional in the feed. `Taskfile.yml:92` even calls ffprobe "optional".
- fix: Catch `FileNotFoundError` once (e.g. in `_run_ffprobe`). Log a single warning ("ffprobe not found; durations omitted") and return `None` without caching the failure, so installing ffprobe later fixes it. Add a test. If DOCKER-07 lands, skip this.
- effort: S
- depends-on: DOCKER-07 (either/or)

### DOCKER-09 tini is not PID 1 while the boot generator runs
- severity: low
- evidence:
  - `Dockerfile:63`: `ENTRYPOINT ["/entrypoint.sh"]`.
  - `entrypoint.sh:30` runs the generator under `/bin/sh` as PID 1.
  - Only `entrypoint.sh:40` `exec /sbin/tini -- $RUNAS caddy ...` makes tini PID 1.
  - `docs/runtime.md:35-36` credits tini with reaping ffprobe zombies.
- problem: During boot generation, PID 1 is `sh` with no signal handlers. The kernel ignores SIGTERM for PID 1 in that state, so a `docker stop` mid-generation waits the full 10 s and then SIGKILLs. That can interrupt the cache or XML write. The atomic replace protects the XML file, though not the in-progress work. ffprobe runs only in that phase, and `subprocess.run` reaps its own children, so the runtime.md rationale is wrong. Caddy-phase signal handling is correct: tini forwards to su-exec, which `exec`s caddy.
- fix: Use `ENTRYPOINT ["/sbin/tini", "--", "/entrypoint.sh"]` and change the last line to `exec $RUNAS caddy run ...`. Update the runtime.md wording.
- effort: S
- depends-on: none

### DOCKER-10 Healthcheck depends on `browse`, logs every 30 s, and has no start period
- severity: low
- evidence:
  - `Dockerfile:61`: `HEALTHCHECK CMD wget -q -O- http://localhost:${SERVICE_PORT}/ || exit 1`.
  - `Caddyfile:22-25` access-logs every request to stdout.
- problem:
  - It only passes because `browse` renders `/`. Removing browse (DOCKER-02) makes the container permanently unhealthy.
  - Every probe renders and downloads the full root listing and writes an access-log line. That is one noise line every 30 s in `docker compose logs`.
  - With default `--start-period=0s`, a long first-run generation on a big library runs before Caddy starts and can mark the container unhealthy.
- fix: Add `handle /healthz { respond "ok" 200 }` plus `log_skip /healthz` (or a `@health` matcher) in the Caddyfile. Use `HEALTHCHECK --interval=30s --timeout=3s --start-period=60s CMD wget -q --spider http://127.0.0.1:${SERVICE_PORT}/healthz || exit 1`.
- effort: S
- depends-on: none (prerequisite of DOCKER-02)

### DOCKER-11 One-year `immutable` cache on MP3s conflicts with fixing an episode in place
- severity: low
- evidence: `Caddyfile:11`: `header @mp3 Cache-Control "public, max-age=31536000, immutable"`
- problem: GUIDs are derived from the filename, and AGENTS.md says "renaming breaks subscriber history". The natural way to fix a bad upload is therefore to overwrite the file under the same name. With `immutable` and a 1-year max-age, browsers, CDNs and some podcast clients never revalidate, so the old audio keeps being served. Caddy already sends ETag/Last-Modified from `file_server`, so revalidation is cheap.
- fix: Use `public, max-age=86400` (or a week) without `immutable` for MP3s. Keep `Content-Type "audio/mpeg"`: it is not redundant. Go's built-in MIME table has no `.mp3` entry and the Alpine base ships no `/etc/mime.types`, so MP3s without an ID3 header would otherwise sniff as `application/octet-stream`.
- effort: S
- depends-on: none

### DOCKER-12 Caddy admin API left on; no basic response headers
- severity: low
- evidence: The `Caddyfile` has no global options block. Caddy's default is an admin API on `localhost:2019`. There is no `header` for `X-Content-Type-Options` or `-Server`.
- problem: Only the file server is used. No `caddy reload` or API call happens anywhere (`entrypoint.sh:40` uses `caddy run`). The admin endpoint is still an open, unauthenticated config API inside the container, reachable from any process there, and in `network_mode: host` setups from the host. For a static audio and feed host the missing headers have low impact. `nosniff` is still cheap and useful, given that user-uploaded files are served next to XML.
- fix: Add a global block `{ admin off }`. Add `header -Server` and `header X-Content-Type-Options nosniff`. Do not add CSP/HSTS: the container serves plain HTTP behind the user's proxy, and HSTS belongs there.
- effort: S
- depends-on: none

### DOCKER-13 `docs/runtime.md` and Dockerfile comments describe a pipeline that no longer exists
- severity: low
- evidence:
  - `docs/runtime.md:7` gives the example "`caddy=2.8.4-r0`", and `docs/runtime.md:13` says "**Caddy**, ffmpeg, tini, su-exec, ca-certificates: Not pinned". In fact `Dockerfile:4` pins `caddy:2.11.4-alpine` from the official image.
  - `docs/runtime.md:20`: "All releases are scanned by Trivy for CVEs **before publishing**". In fact `release.yml:99-109` pushes (`push: true`, including `latest`) and only then scans the pushed digest (`release.yml:118-127`).
  - `docs/runtime.md:35-36` gives the tini/ffprobe zombie rationale (see DOCKER-09).
  - `Dockerfile:43`: "supervisord logs/pid under /tmp". supervisord was removed in `85334b4`.
- problem: These docs mislead the rework itself. The Trivy claim matters most: a CRITICAL finding fails the job only after the image is already public under `latest`.
- fix: Rewrite the pinning section to describe what is actually there (the official Caddy stage, unpinned apk, `apk upgrade`). Either correct the Trivy sentence or reorder the release workflow to build, `load`, scan, then push. That reorder belongs to the CI area. Delete the supervisord comment.
- effort: S
- depends-on: DOCKER-09

### DOCKER-14 ADRs out of date with the code they govern
- severity: low
- evidence:
  - `docs/adr/0001-root-only-container-runtime.md:5` is "Superseded" by the PUID/su-exec runtime, but no ADR records that decision; it points at `docs/runtime.md`. Its References cite `RELEASE_NOTES_v1.0.1.md`, which is not tracked (`git ls-files` returns nothing), and `adr/0002:55` cites it too.
  - `docs/adr/0002-env-var-contract.md:24-32`: the "canonical" table omits `CACHE_ROOT`, `LOG_LEVEL`, `PUID` and `PGID`, and its line refs are stale (`config.py:20-24`, `Dockerfile:23-28`; ENV is now `Dockerfile:44-57`).
  - `docs/adr/0003-duration-cache-location.md:5` is "Accepted", but its context problems are all fixed in code (`media.py:22-23`, `media.py:58-73`, `media.py:84-88`).
- problem: The owner turns docs into tickets. Stale ADRs will regenerate already-closed work, and they hide the real current decision: dual root/non-root runtime with chown and su-exec.
- fix: Add ADR 0004 "PUID/PGID drop with su-exec; pinned `user:` as hardened mode" and mark 0001 as superseded by it. Refresh the 0002 table to the full env contract, matching whichever DOCKER-06 option is chosen. Drop line-number refs in favour of symbol names, and remove the dead RELEASE_NOTES links.
- effort: S
- depends-on: DOCKER-06

### DOCKER-15 `RUN_ON_START` parsing differs between entrypoint and code; empty install reports failure
- severity: low
- evidence:
  - `entrypoint.sh:28`: `if [ "${RUN_ON_START:-true}" = "true" ]` (case-sensitive), while `config.py:25` uses `v.lower() == "true"`. ADR 0002 says "accept only `"true"` (case-insensitive)".
  - `cli.py:175`: `return count > 0` together with `entrypoint.sh:30-31` produces "Generator exited non-zero; continuing to serve existing content".
- problem: `RUN_ON_START=True` or `TRUE` silently skips boot generation, against the documented contract. On a fresh install with no configs yet, the very first log line looks like an error. Conversely, a run where 1 of 5 podcasts failed exits 0.
- fix: Lower-case in the entrypoint (`case "$RUN_ON_START" in [Tt][Rr][Uu][Ee])`, or `tr`). Make the exit code mean "some configured podcast failed" (`ok < len(configs)`), and treat "no configs" as exit 0 with an info log.
- effort: S
- depends-on: none

### DOCKER-16 Base images pinned by tag only, with no update bot; dead build args
- severity: low
- evidence:
  - `Dockerfile:4` `FROM caddy:2.11.4-alpine AS caddy` and `Dockerfile:6` `FROM python:3.12-alpine3.22`, with no `@sha256:` digests.
  - No `.github/dependabot.yml` or Renovate config is tracked.
  - `ci.yml:102-105` and `release.yml:113-116` pass `VERSION`, `BUILD_DATE` and `VCS_REF` build args, but the Dockerfile declares no `ARG` (the OCI labels come from `metadata-action`).
- problem: Tags are mutable, and the bumps that fix CVEs, such as `c445816`, are manual. Python 3.12 is security-fix-only, and Alpine 3.22 is no longer the newest stable. That is fine today, but nothing will prompt the next bump. The unused build args suggest metadata that is never applied.
- fix: Add a Dependabot config with `package-ecosystem: docker` (directory `/docker/podcastify`), `pip` and `github-actions`. It is native and needs no extra tooling. Optionally pin digests, which Dependabot will maintain. Delete the three `build-args` blocks.
- effort: S
- depends-on: none

### DOCKER-17 `cache/` bind-mount directory is not ignored by git or by the build context
- severity: low
- evidence:
  - `docker-compose.yml:29`: `- ./cache:/app/.cache:rw` creates `./cache/`, which holds `.podcastify-cache.json` and Caddy's `caddy/` state.
  - `.gitignore` ignores `.podcastify-cache.json` and `public/*`/`podcasts/*` but not `cache/`.
  - `.dockerignore:1-7` excludes neither `cache/` nor `.venv/`, `htmlcov/` or `.pytest_cache/`.
- problem: After the first `task docker:up`, `git status` shows `cache/` with Caddy's autosave and cert-storage dirs, which are easy to commit by accident. A local `.venv` is sent as build context on every build, though it is not copied into the image (the Dockerfile COPYs only named paths).
- fix: Add `cache/` to `.gitignore`. Switch `.dockerignore` to an allowlist (`*`, then `!app.py`, `!requirements.txt`, `!podcastify/`, `!docker/podcastify/`).
- effort: S
- depends-on: none

### DOCKER-18 Compose file duplicates image defaults and publishes on all interfaces
- severity: info
- evidence:
  - `docker-compose.yml:12-24` re-declares every variable already set by `Dockerfile:44-54` with identical defaults.
  - `docker-compose.yml:10` `"${HOST_PORT:-8080}:${SERVICE_PORT:-8080}"` binds 0.0.0.0, while `docs/deployment.md:99-115` tells reverse-proxy users to proxy `localhost:8080`.
  - `:rw` on `docker-compose.yml:27-29` is the default anyway.
- problem: Two sources of truth for defaults drift (see DOCKER-06). Behind a reverse proxy, the plain-HTTP port stays reachable from the LAN or internet, which bypasses the proxy's TLS and any auth the user put there.
- fix: Keep only `PUBLIC_BASE_URL`, `PUID`, `PGID` and the port in compose; the image holds the rest. In the reverse-proxy docs, show `127.0.0.1:${HOST_PORT}:${SERVICE_PORT}`. Drop the `:rw` suffixes.
- effort: S
- depends-on: DOCKER-06

---

## Summary

| id | severity | effort |
|---|---|---|
| DOCKER-01 | high | S |
| DOCKER-02 | high | S |
| DOCKER-03 | medium | S |
| DOCKER-04 | medium | S |
| DOCKER-05 | medium | M |
| DOCKER-06 | medium | S |
| DOCKER-07 | medium | M |
| DOCKER-08 | low | S |
| DOCKER-09 | low | S |
| DOCKER-10 | low | S |
| DOCKER-11 | low | S |
| DOCKER-12 | low | S |
| DOCKER-13 | low | S |
| DOCKER-14 | low | S |
| DOCKER-15 | low | S |
| DOCKER-16 | low | S |
| DOCKER-17 | low | S |
| DOCKER-18 | info | S |

## Already good (no ticket)

- The Caddy binary is copied from the official `caddy:2.11.4-alpine` stage rather than the lagging apk package (`Dockerfile:1-4,18`). This is a sensible, minimal multi-stage use. A separate Python builder stage would gain nothing here, since both deps install as wheels.
- Layer order is right: `requirements.txt` and `pip install --no-cache-dir` come before the app COPY, and `apk --no-cache` is used.
- Removing supervisord in favour of one foreground Caddy under tini, with `su-exec` (tiny) instead of gosu or sudo, is the right lightweight choice. Once Caddy runs, signal forwarding works: tini, then su-exec `exec`, then caddy.
- The hardened mode in `docs/deployment.md:126-139` (`user:` + `read_only` + `cap_drop: ALL` + `no-new-privileges` + tmpfs `/tmp`) is correct for the current entrypoint. Caddy's state is relocated to the cache volume through `XDG_*`, so nothing writes to the root FS.
- The duration cache lives outside the served root (`CACHE_ROOT`), and `hide .*` covers dotfiles in every directory (per the Caddy docs, a pattern without a separator matches anywhere).
- Feed writes are atomic and world-readable (`cli.py:127-134`). Caddy can never serve a half-written XML.
- `encode gzip` uses Caddy's default content-type match list, so feeds (`application/rss+xml`) are compressed and MP3s are not, and byte-range requests for audio are left intact. The `Content-Type` overrides for `.xml` and `.mp3` are justified.
- `Access-Control-Allow-Origin "*"` is appropriate for public feeds consumed by web players. No ticket.
- Generator logs split INFO to stdout and WARNING+ to stderr, and `PYTHONUNBUFFERED=1` keeps them ordered in `docker logs`. `docs/deployment.md:76-87` explains log visibility accurately.
- `docs/deployment.md` is otherwise accurate against the real files: the env table, Caddyfile copy, the two runtime modes and the capability warning all match.

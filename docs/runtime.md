# Runtime Architecture

## Container & Package Pinning

### Rationale

The base image `python:3.12-alpine3.22` pins the Alpine and Python versions. nginx comes from Alpine's package repository, so `apk upgrade` patches it with the rest of the base. An upstream Go binary such as Caddy cannot be patched that way: its bundled dependencies wait for the next upstream release (see [ADR 0009](adr/0009-nginx-replaces-caddy.md)). The Alpine packages `tini`, `su-exec`, `ca-certificates` and `nginx` are installed without version pins, after `apk upgrade --no-cache` has patched the base packages. Pinning those packages to patch revisions breaks as Alpine moves to newer revisions, so the maintenance burden outweighs the benefit.

### Decision

- **nginx, tini, su-exec, ca-certificates**: Not pinned to specific patch revisions; `apk upgrade` runs at build time.
- **Rationale**: The base image `python:3.12-alpine3.22` provides sufficient reproducibility for development and deployment. In production, users should run specific image digests (via `docker pull image@sha256:...`) rather than tags to ensure exact reproducibility.
- **Alternative**: If reproducibility across releases becomes critical, maintain a separate `alpine.versions.lock` file and use a more sophisticated build process (e.g., a shell script to query apk repos and pin available versions).

### Security

- Pull requests build the image without pushing it, then smoke test it.
- Images are pushed to Docker Hub only on tagged releases. The release workflow rejects a tag that is not CalVer (`vYYYY.M.PATCH`, month without zero padding, optional `-rc.N`).
- A release pushes the image as `YYYY.M.PATCH` (the tag without the `v`), plus `latest` for a stable tag. A prerelease tag pushes only its exact version and does not move `latest`. There is no `v`-prefixed and no `major.minor` tag.
- A release builds the amd64 image locally without pushing, scans it with Trivy (CRITICAL and HIGH findings with a fix fail the job), and only then pushes the multi-arch image. A failed scan publishes nothing.
- An SBOM is attached to each release image, and one signed provenance attestation is published for its digest (BuildKit's own provenance is off). Check it with `gh attestation verify oci://docker.io/fnayou/podcastify:YYYY.M.PATCH --repo fnayou/podcastify`.

## Process Management

### Tini as PID 1, nginx in the foreground

nginx runs in the foreground under `tini` — no supervisor. The generator runs
once at boot, plus the optional background watcher described below. `tini` is
PID 1 for the whole container life: the image entrypoint is
`["/sbin/tini", "--", "/entrypoint.sh"]`, and the script ends with:

```bash
exec $RUNAS nginx -c /tmp/nginx/nginx.conf
```

`tini` forwards signals, so `docker stop` ends the container promptly both
during the boot generation and once nginx serves. Without it, the shell would be
PID 1 during generation, ignore SIGTERM, and be killed after the stop timeout.
The generator starts no child processes of its own: durations are read in-process.

`RUN_ON_START` is read case-insensitively by the entrypoint, with the same
values as the generator: `true/yes/1/on` run the generator at boot.

### Automatic regeneration

With `GENERATE_INTERVAL` set to a whole number of seconds above `0`, the
entrypoint starts `app.py watch --interval <seconds>` in the background under
the same `$RUNAS`, then `exec`s nginx. Every interval the watcher compares a
fingerprint of the configs (`PODCASTS_ROOT/*-podcast.yaml`) and the media
(`PUBLIC_ROOT/<name>/*` with a known media extension): path, size and mtime.
When it changes, the watcher regenerates every feed. Polling needs no extra
package and works on SMB/NFS and Docker Desktop bind mounts, where inotify does
not fire. The default `0` turns it off; any other value warns and turns it off.

The watcher starts from the state left by the boot generation and only acts on
later changes. If the boot generation exited non-zero, the watcher starts with
`--initial-run` and regenerates on its first check, so a failed boot run is
retried and logged again rather than hidden. A failed regeneration logs an
error and waits for the next change. The watcher is a child of `tini`, which
reaps it; it stops with the container when nginx exits.

The generator writes `<name>.xml` only when its content differs from the file
on disk, ignoring `<lastBuildDate>`. An unchanged feed keeps its file and
mtime, so podcast clients do not refetch it.

### Non-root via PUID/PGID

The image supports two runtimes (see `entrypoint.sh` and [ADR 0005](adr/0005-puid-pgid-runtime.md)):

- **Root start (default/convenience):** the entrypoint chowns only what the app
  writes to `PUID`/`PGID` (default `1000`): `CACHE_ROOT` recursively,
  `PUBLIC_ROOT` itself and the feeds `PUBLIC_ROOT/*.xml`. Media under
  `PUBLIC_ROOT/<name>/` and the configs in `PODCASTS_ROOT` keep their host
  owner. Paths that already match are skipped, and a failed chown prints its
  error and a warning. It then drops privileges with `su-exec`. Adapts to any
  host bind-mount owner (NAS/desktop). `$RUNAS` = `su-exec <uid>:<gid>`.
- **Non-root start (hardened):** when the operator pins the container `user:`,
  the entrypoint skips chown/`su-exec` and runs directly. This is compatible
  with `cap_drop: ALL` + `read_only` because no privileged ops are performed —
  the bind-mounts must already be owned by that uid. `$RUNAS` is empty.

`entrypoint.sh generate [--dry-run]` runs the generator once under the same
`$RUNAS` and exits, after the same preparation. `task podcastify:generate` and
the documented `docker compose exec podcastify /entrypoint.sh generate` use it,
so on-demand runs write files as `PUID`/`PGID`, never root.

The entrypoint renders `/etc/nginx/podcastify.conf` (the shipped
`docker/podcastify/nginx.conf`, with `SERVICE_PORT` filled in) to
`/tmp/nginx/nginx.conf`. nginx keeps its pid file and temp directories under
`/tmp/nginx` too, so the root filesystem can be read-only as long as `/tmp` is a
tmpfs. The container's stdout pipe belongs to root, so nginx cannot open
`/dev/stdout` after `su-exec`: it logs errors to stderr and writes the access
log to a FIFO that the entrypoint copies to stdout.

## Healthcheck

A wget-based healthcheck is configured in the Dockerfile. It requests `/healthz`, a fixed `200 ok` response that nginx does not access-log, and allows a 120 second start period for the first generation on a large library:

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=120s CMD ["/bin/sh", "-c", "wget -q --spider http://127.0.0.1:${SERVICE_PORT}/healthz || exit 1"]
```

This verifies that nginx is responding on the configured port.

## Index page at `/`

The nginx config needs no rule for the index. nginx serves `index.html` for `/` when `/app/public/index.html` exists. Without it nginx answers 403 for a directory, and `error_page 403 = @not_found` turns that into 404. Directory listing is off, and a dotfile location answers 404, which keeps the generator's temp files unreachable. The generator writes the file only with `PUBLISH_INDEX=true`; see [Index Page](../website/deployment.md#index-page). The smoke test checks both states on the built image.

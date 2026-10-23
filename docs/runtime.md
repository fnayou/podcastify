# Runtime Architecture

## Container & Package Pinning

### Rationale

Alpine Linux package versions for python:3.12-alpine3.22 are managed by Alpine's package repository and are regularly updated. Attempting to pin to specific patch versions (e.g., `caddy=2.8.4-r0`) often results in dependency conflicts as Alpine moves to newer minor/patch releases that are incompatible with the pinned versions.

Since the base image `python:3.12-alpine3.22` already pins the Alpine version and Python version, and our Dockerfile rebuilds are infrequent (only on explicit rebuilds), the practical benefit of pinning individual apk packages is outweighed by the maintenance burden of tracking and updating pinned versions.

### Decision

- **Caddy, ffmpeg, tini, su-exec, ca-certificates**: Not pinned to specific patch revisions.
- **Rationale**: The base image `python:3.12-alpine3.22` provides sufficient reproducibility for development and deployment. In production, users should run specific image digests (via `docker pull image@sha256:...`) rather than tags to ensure exact reproducibility.
- **Alternative**: If reproducibility across releases becomes critical, maintain a separate `alpine.versions.lock` file and use a more sophisticated build process (e.g., a shell script to query apk repos and pin available versions).

### Security

- Container images are built only on tagged releases (`v*.*.*`).
- All releases are scanned by Trivy for CVEs before publishing.
- SBOM and provenance attestations are attached to each release.

## Process Management

### Tini as PID 1, Caddy in the foreground

Caddy is the only long-running process (the generator runs once at boot), so it
runs in the foreground under `tini` — no supervisor. `tini` is PID 1 for the
whole container life: the image entrypoint is
`["/sbin/tini", "--", "/entrypoint.sh"]`, and the script ends with:

```bash
exec $RUNAS caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
```

`tini` forwards signals, so `docker stop` ends the container promptly both
during the boot generation and once Caddy serves. Without it, the shell would be
PID 1 during generation, ignore SIGTERM, and be killed after the stop timeout.
ffprobe children are reaped by `subprocess.run` itself.

`RUN_ON_START` is read case-insensitively by the entrypoint, with the same
values as the generator: `true/yes/1/on` run the generator at boot.

### Non-root via PUID/PGID

The image supports two runtimes (see `entrypoint.sh`):

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

Caddy data/config are relocated under `XDG_DATA_HOME`/`XDG_CONFIG_HOME`
(`/app/.cache/caddy`, on the cache volume) so nothing is written to the
read-only root filesystem.

## Healthcheck

A wget-based healthcheck is configured in the Dockerfile. It requests `/healthz`, a fixed `200 ok` response that Caddy does not access-log, and allows a 120 second start period for the first generation on a large library:

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=120s CMD wget -q --spider http://127.0.0.1:${SERVICE_PORT}/healthz || exit 1
```

This verifies that Caddy is responding on the configured port.

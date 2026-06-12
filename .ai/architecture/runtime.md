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
runs in the foreground under `tini` — no supervisor. The entrypoint invokes
`tini` as PID 1:

```bash
exec /sbin/tini -- $RUNAS caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
```

`tini` ensures zombie process cleanup when ffprobe (spawned by MediaProcessor)
exits, preventing resource leaks in long-running container scenarios.

### Non-root via PUID/PGID

The image supports two runtimes (see `entrypoint.sh`):

- **Root start (default/convenience):** the entrypoint chowns the writable dirs
  to `PUID`/`PGID` (default `1000`) and drops privileges with `su-exec`. Adapts
  to any host bind-mount owner (NAS/desktop). `$RUNAS` = `su-exec <uid>:<gid>`.
- **Non-root start (hardened):** when the operator pins the container `user:`,
  the entrypoint skips chown/`su-exec` and runs directly. This is compatible
  with `cap_drop: ALL` + `read_only` because no privileged ops are performed —
  the bind-mounts must already be owned by that uid. `$RUNAS` is empty.

Caddy data/config are relocated under `XDG_DATA_HOME`/`XDG_CONFIG_HOME`
(`/app/.cache/caddy`, on the cache volume) so nothing is written to the
read-only root filesystem.

## Healthcheck

A simple wget-based healthcheck is configured in the Dockerfile:

```dockerfile
HEALTHCHECK CMD wget -q -O- http://localhost:${SERVICE_PORT}/ || exit 1
```

This verifies that Caddy is responding on the configured port.

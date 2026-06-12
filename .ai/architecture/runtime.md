# Runtime Architecture

## Container & Package Pinning

### Rationale

Alpine Linux package versions for python:3.12-alpine3.22 are managed by Alpine's package repository and are regularly updated. Attempting to pin to specific patch versions (e.g., `caddy=2.8.4-r0`) often results in dependency conflicts as Alpine moves to newer minor/patch releases that are incompatible with the pinned versions.

Since the base image `python:3.12-alpine3.22` already pins the Alpine version and Python version, and our Dockerfile rebuilds are infrequent (only on explicit rebuilds), the practical benefit of pinning individual apk packages is outweighed by the maintenance burden of tracking and updating pinned versions.

### Decision

- **Caddy, ffmpeg, supervisor, tini, ca-certificates**: Not pinned to specific patch revisions.
- **Rationale**: The base image `python:3.12-alpine3.22` provides sufficient reproducibility for development and deployment. In production, users should run specific image digests (via `docker pull image@sha256:...`) rather than tags to ensure exact reproducibility.
- **Alternative**: If reproducibility across releases becomes critical, maintain a separate `alpine.versions.lock` file and use a more sophisticated build process (e.g., a shell script to query apk repos and pin available versions).

### Security

- Container images are built only on tagged releases (`v*.*.*`).
- All releases are scanned by Trivy for CVEs before publishing.
- SBOM and provenance attestations are attached to each release.

## Process Management

### Tini as PID 1

The entrypoint script invokes `tini` as PID 1:

```bash
exec /sbin/tini -- /usr/bin/supervisord -c /etc/supervisord.conf
```

This ensures zombie process cleanup when ffprobe (spawned by MediaProcessor) exits, preventing resource leaks in long-running container scenarios.

## Healthcheck

A simple wget-based healthcheck is configured in the Dockerfile:

```dockerfile
HEALTHCHECK CMD wget -q -O- http://localhost:${SERVICE_PORT}/ || exit 1
```

This verifies that Caddy is responding on the configured port.

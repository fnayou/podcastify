# 0005 - PUID/PGID drop with su-exec; pinned `user:` as hardened mode

## Status

Accepted. Supersedes [0001](0001-root-only-container-runtime.md).

## Context

ADR 0001 ran everything as root so bind-mounted `public/` and `podcasts/`
never failed on NAS and desktop hosts. The cost: files written under `public/`
and the cache were root-owned on the host. Earlier builds that created a fixed
app user failed the other way, because the host uid/gid did not map into the
container.

## Decision

The image supports two runtimes, chosen by the uid the container starts with
(`docker/podcastify/entrypoint.sh`):

- **Root start (default):** the entrypoint creates `PUBLIC_ROOT`,
  `PODCASTS_ROOT` and `CACHE_ROOT`, then chowns only what the app writes to
  `PUID`/`PGID` (default `1000`): `CACHE_ROOT` recursively, `PUBLIC_ROOT`
  itself and `PUBLIC_ROOT/*.xml`. Media and configs keep their host owner. A
  path that already has the right owner is skipped, and a failed chown prints a
  warning and continues. It then runs the generator, the watcher and Caddy
  through `su-exec <PUID>:<PGID>`. This needs the `CHOWN`, `SETUID` and
  `SETGID` capabilities.
- **Non-root start (hardened):** when the operator pins the container user
  (compose `user:`), the entrypoint skips chown and `su-exec` and runs as that
  user. This works with `cap_drop: ALL` and `read_only: true`, because no
  privileged operation is needed. The bind mounts must already be owned by
  that uid.

`entrypoint.sh generate [--dry-run]` runs the generator once under the same
user and exits, so on-demand runs write files as `PUID`/`PGID`, never as root.

## Consequences

- Generated feeds and the duration cache are owned by `PUID`/`PGID` in the
  default runtime, not by root.
- Users on any host bind-mount owner set `PUID` and `PGID` to match it; no
  `user:` override is needed.
- Hardened deployments pin `user:`, drop all capabilities and prepare the
  mount ownership themselves.
- The image carries `su-exec` (`apk add` in `docker/podcastify/Dockerfile`).
- `PUID` and `PGID` are part of the environment contract of ADR 0002.

## References

- `docker/podcastify/entrypoint.sh`
- `docker/podcastify/Dockerfile`
- `docs/runtime.md`
- [0001](0001-root-only-container-runtime.md), [0002](0002-env-var-contract.md)

# 0001 - Run container as root

## Status

Superseded by [0005](0005-puid-pgid-runtime.md): the entrypoint now drops privileges via `PUID`/`PGID` with `su-exec` and supports a pinned non-root `user:`.

## Context

Earlier builds created a dedicated app user and `chown`'d `/app/public` and
`/app/podcasts` at startup. This broke on NAS/desktop bind-mounts where host
UID/GID don't map cleanly into the container, causing permission errors when
writing `public/*.xml`.

## Decision

Run the container as root — no `USER` directive and no chown logic in
`docker/podcastify/Dockerfile`. Bind-mounted `public/` and `podcasts/` stay
`:rw`.

## Consequences

- Files written under `public/` are root-owned on the host.
- Users needing host-user ownership can override with
  `user: "${PUID}:${PGID}"` in their own compose file.
- Simplifies the Dockerfile and entrypoint (no chown step, fewer NAS edge
  cases).

## References

- `docker/podcastify/Dockerfile`

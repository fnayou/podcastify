# 0004 - Container path variables are image defaults, not settings

## Status

Accepted

## Context

`PODCASTS_ROOT`, `PUBLIC_ROOT` and `CACHE_ROOT` were passed through
`docker-compose.yml`, listed in `.env.example` and in the `docs/deployment.md`
table. Only the generator honoured them. Caddy serves `/app/public`
(`docker/podcastify/Caddyfile`), the entrypoint prepares `/app/public`,
`/app/podcasts` and `/app/.cache`, and the Dockerfile points Caddy's state at
`/app/.cache/caddy`. Setting `PUBLIC_ROOT=/data/public` therefore made the
generator write feeds where Caddy did not look, and no error was reported
(audit finding DOCKER-06).

## Decision

Option (a) of the audit: the three variables are internal defaults of the image
(`docker/podcastify/Dockerfile`) and `podcastify/config.py`. They are removed
from `docker-compose.yml`, `.env.example`, the `docs/deployment.md` table and
the README example. To store data elsewhere, change the host side of the volume
mounts. The container paths stay `/app/public`, `/app/podcasts` and
`/app/.cache`.

`Config` still reads the variables from the environment, so tests and local
runs outside the container can point at other directories. That is not a
supported way to configure the image.

## Consequences

- Compose no longer forwards the three variables, so a leftover `PUBLIC_ROOT`
  in a user's `.env` has no effect on the container.
- ADR 0002 no longer lists `PODCASTS_ROOT` and `PUBLIC_ROOT` in the contract.
- ADR 0003 still describes the cache location; `CACHE_ROOT` is now an image
  default, not a user setting.
- `tests/test_env_contract.py` fails if compose, `.env.example` or the
  deployment table offer a variable that ADR 0002 does not list, or bring the
  path variables back.
- Honouring the variables everywhere (option b) stays possible later, but needs
  the Caddyfile, the entrypoint and the Dockerfile to read them.

## References

- `docs/audit/2026-10/docker.md` (DOCKER-06)
- `docker/podcastify/Dockerfile`
- `docker/podcastify/Caddyfile`
- `docker-compose.yml`

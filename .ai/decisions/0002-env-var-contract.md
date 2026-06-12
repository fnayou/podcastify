# 0002 - Environment variable contract (PORT -> SERVICE_PORT)

## Status

Accepted

## Context

The variable controlling the in-container Caddy listen port was renamed from
`PORT` to `SERVICE_PORT` in the v1.0.1 runtime simplification, and `HOST_PORT`
was introduced for the host-side mapping. The generator itself only ever reads
`PUBLIC_BASE_URL`, `PODCASTS_ROOT`, `PUBLIC_ROOT`, `RUN_ON_START`, and
`PUBLISH_XML` (`podcastify/config.py:20-24`); it does not read any port
variable. Caddy binds `{$SERVICE_PORT}` (`docker/podcastify/Caddyfile:1`).

After two reboots the docs drifted: `docs/deployment.md` still teaches `PORT`,
which is silently ignored by the shipped image. This ADR fixes the contract so
all surfaces (Dockerfile, compose, Caddy, docs, .env.example) agree.

## Decision

The canonical environment contract is:

| Variable | Read by | Default | Purpose |
|---|---|---|---|
| `HOST_PORT` | compose only | `8080` | Host port published to the outside |
| `SERVICE_PORT` | Caddy, Dockerfile, compose | `8080` | In-container Caddy listen port |
| `PUBLIC_BASE_URL` | generator (`Config.BASE_URL`) | `http://localhost:8080` | Base URL embedded in enclosure/image links |
| `PODCASTS_ROOT` | generator | `/app/podcasts` | YAML config dir |
| `PUBLIC_ROOT` | generator | `/app/public` | Media + generated feeds dir |
| `RUN_ON_START` | generator, entrypoint | `true` | Run generator once at boot |
| `PUBLISH_XML` | generator | `true` | Write `<name>.xml` (false = dry run) |

`PORT` is retired. It must not appear in any tracked file except a one-line
migration note.

## Consequences

- `docs/deployment.md` must be rewritten to use `SERVICE_PORT` and the shipped
  Caddyfile (`{$SERVICE_PORT}`, `hide .*`).
- `Config.BASE_URL` reads `PUBLIC_BASE_URL`, not `BASE_URL`; KB/glossary must
  not call the env var "BASE_URL" (the *attribute* is `BASE_URL`, the *env key*
  is `PUBLIC_BASE_URL`).
- Boolean env vars (`PUBLISH_XML`, `RUN_ON_START`) accept only `"true"`
  (case-insensitive) via `Config`, which differs from YAML booleans parsed by
  `_coerce_bool` (`true/yes/1/on`). This asymmetry is intentional for now and
  documented here so it is not "fixed" accidentally.

## References

- `podcastify/config.py:20-24`
- `docker/podcastify/Caddyfile:1`
- `docker/podcastify/Dockerfile:23-28`
- `docker-compose.yml:9-18`
- `RELEASE_NOTES_v1.0.1.md`

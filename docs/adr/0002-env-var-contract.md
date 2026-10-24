# 0002 - Environment variable contract (PORT -> SERVICE_PORT)

## Status

Accepted

## Context

The variable controlling the in-container Caddy listen port was renamed from
`PORT` to `SERVICE_PORT` in the v1.0.1 runtime simplification, and `HOST_PORT`
was introduced for the host-side mapping. The generator itself only ever reads
`PUBLIC_BASE_URL`, `RUN_ON_START`, `PUBLISH_XML`, `PUBLISH_INDEX` and `LOG_LEVEL`, plus the
internal path defaults of ADR 0004 (`podcastify/config.py`); it does not read
any port variable. Caddy binds `{$SERVICE_PORT}` (the site address in `docker/podcastify/Caddyfile`).

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
| `PUID` | entrypoint, compose | `1000` | uid the container drops to when started as root |
| `PGID` | entrypoint, compose | `1000` | gid the container drops to when started as root |
| `RUN_ON_START` | generator, entrypoint | `true` | Run generator once at boot |
| `GENERATE_INTERVAL` | entrypoint | `0` | Seconds between change checks of configs and media; `0` = off |
| `PUBLISH_XML` | generator | `true` | Write `<name>.xml` (false = dry run) |
| `PUBLISH_INDEX` | generator | `false` | Write `index.html` listing the feeds; only effective while `PUBLISH_XML` is on |
| `LOG_LEVEL` | generator | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR` |

`PODCASTS_ROOT`, `PUBLIC_ROOT` and `CACHE_ROOT` are not part of the contract:
they are image-internal defaults, see ADR 0004.

`PORT` is retired. It must not appear in any tracked file except a one-line
migration note.

## Consequences

- `docs/deployment.md` must be rewritten to use `SERVICE_PORT` and the shipped
  Caddyfile (`{$SERVICE_PORT}`, `hide .*`).
- `Config.BASE_URL` reads `PUBLIC_BASE_URL`, not `BASE_URL`; KB/glossary must
  not call the env var "BASE_URL" (the *attribute* is `BASE_URL`, the *env key*
  is `PUBLIC_BASE_URL`).
- Boolean env vars (`PUBLISH_XML`, `PUBLISH_INDEX`, `RUN_ON_START`) and YAML booleans share one
  parser, `_coerce_bool` (`podcastify/config.py`): `true/yes/1/on` and
  `false/no/0/off`, case-insensitive. Any other string is read as false and
  logged as a warning. This replaces the earlier "only `true`" env rule. The
  entrypoint reads `RUN_ON_START` the same way: `true/yes/1/on`,
  case-insensitive, run the generator at boot.

## References

- `Config` and `_coerce_bool` in `podcastify/config.py`
- site address in `docker/podcastify/Caddyfile`
- `ENV` block of `docker/podcastify/Dockerfile`
- `environment:` list of `docker-compose.yml`

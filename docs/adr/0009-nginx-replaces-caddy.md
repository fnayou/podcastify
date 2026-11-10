# 0009 - nginx from Alpine replaces Caddy

## Status

Accepted on 2026-11-10. Tracked by issue #135, which blocks the first CalVer release in issue #48.

## Context

The image served `/app/public` with Caddy. The Dockerfile copied the Caddy binary from the official `caddy` image, because the Alpine `caddy` package lagged upstream. A copied Go binary carries its own Go toolchain and dependencies, and `apk upgrade` cannot patch them. Only a new upstream Caddy release can.

That stalled the release. `v2026.10.0` failed the Trivy gate on `caddy:2.11.7-alpine` (Go 1.26.8, `golang.org/x/net` 0.59.0). Caddy 2.11.9 cleared those four CVEs but still failed on CVE-2026-78661 (`x/net` 0.60.0, fixed in 0.62.0). A `.trivyignore` entry or an xcaddy build was ruled out on 2026-10-28.

The Caddyfile used very little of Caddy: one site with a fixed health response, per-extension headers, gzip, dotfile hiding and a plain file server.

## Decision

Serve the files with nginx from the Alpine package repository (`apk add nginx`, 1.28 on Alpine 3.22). `docker/podcastify/nginx.conf` replaces the `Caddyfile` and covers every directive except two:

- `admin off` has no equivalent, because nginx has no admin API.
- `header -Server` has no equivalent in stock nginx. `server_tokens off` removes the version, and `Server: nginx` remains.

The entrypoint renders the config to `/tmp/nginx/nginx.conf`, filling in `SERVICE_PORT`, and starts nginx under `tini` as before. Everything nginx writes goes under `/tmp/nginx`, so the hardened runtime (read-only root, pinned `user:`, `cap_drop: ALL`, tmpfs on `/tmp`) keeps working. Errors go to stderr. The access log goes through a FIFO that the entrypoint copies to stdout, because after `su-exec` the container's stdout pipe is owned by root and nginx cannot open `/dev/stdout`.

## Consequences

- Security patches for nginx arrive with `apk upgrade` at build time. The Trivy gate no longer waits on an upstream release.
- The image has no pinned server version, like `tini` and `su-exec`. The Alpine release pins it.
- `Server: nginx` is sent. The old image sent no `Server` header.
- A request for a directory without `index.html` logs an `[error]` line (`directory index ... is forbidden`) before it answers 404. The 404 is unchanged.
- `SERVICE_PORT` must be a number. The entrypoint refuses to start otherwise.
- The `XDG_DATA_HOME` and `XDG_CONFIG_HOME` variables and the Caddy state under `/app/.cache/caddy` are gone. Existing `cache/caddy/` directories on a host are unused and can be deleted.
- Older ADRs still name Caddy and the Caddyfile. They record the decisions as they were.

## References

- Issue #135, issue #48
- [0002](0002-env-var-contract.md), [0004](0004-path-env-vars-are-internal.md), [0005](0005-puid-pgid-runtime.md)

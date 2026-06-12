# Changelog

All notable changes to Podcastify are documented here. See [GitHub Releases](https://github.com/fnayou/podcastify/releases) for artifacts and SBOM/provenance.

## v1.1.1

### Fixed

- **Duration-cache race condition** — `MediaProcessor.warm_durations_parallel`
  ran 4 worker threads that mutated the shared `_duration_cache` while
  `_save_disk_cache` iterated it, raising
  `RuntimeError: dictionary changed size during iteration`. Feeds with many
  uncached episodes (e.g. `rdvx`) failed to regenerate every run. Added a
  `threading.Lock`, an iteration snapshot, and an atomic cache write.
- **Published feeds were `0600`** — `tempfile.mkstemp` creates `0600`, so
  generated `*.xml` were not world-readable. They are now `chmod 0644` before
  the atomic rename.

### Changed

- **Cache disk writes are batched** — the disk cache is now written once after
  parallel warming completes instead of after every probe (was O(N²) writes and
  widened the race window).
- **Runs unprivileged via PUID/PGID** — the container now drops to `PUID`/`PGID`
  (default `1000`) with `su-exec`, or runs directly as a pinned non-root user
  when the operator sets the container `user:` (compatible with
  `cap_drop: ALL` + `read_only`). Caddy data (`XDG_*`) lives under the cache
  volume; nothing writes to the root filesystem.
- **Dropped supervisor** — Caddy (the only long-running process) now runs in the
  foreground under `tini`. Removes the `supervisord.log` root-FS write, the
  `pkg_resources is deprecated` warning, and the non-root `/dev/stdout` EACCES.
- `Caddyfile` reformatted with `caddy fmt` (removes the "not formatted" warning).

## v1.0.1 (Maintenance)

A maintenance release that simplifies the container runtime, fixes common permission/restart issues, and aligns environment variables across Docker, Caddy, and the generator. It also improves CI security scanning and publishing.

### Highlights

- **Simpler runtime (root-only)**
  Reverted to running as root inside the container to avoid NAS/desktop bind-mount edge cases and permission errors when writing `public/*.xml`.

- **One-shot generation on startup**
  The container runs `python /app/app.py generate` once at boot (if `RUN_ON_START=true`) and then serves content. No supervisor loop.

- **Caddy served with explicit service port**
  Caddy now listens on `SERVICE_PORT` (defaults to `8080`) and headers were refined for RSS and static assets.

- **Unified environment variables**
  Introduced `HOST_PORT` and `SERVICE_PORT` for clarity. `PUBLIC_BASE_URL` now defaults to `http://localhost:${HOST_PORT}`.

- **Compose and Caddy alignment**
  `docker-compose.yml` maps `${HOST_PORT}:${SERVICE_PORT}` and passes `SERVICE_PORT` into Caddy. Volumes remain writable with `:rw`.

- **CI hardening (GitHub Actions)**
  Builds & pushes only on semver tags, `latest` only for stable tags. Trivy scans (fail on CRITICAL for tag builds), Docker Scout non-blocking comments on PRs, and fixed provenance attestation by digest.

### Changes (since v1.0.0)

- Dockerfile: removed app user switching and chown logic; kept minimal deps.
- Entrypoint: runs generator once at startup, then starts Caddy.
- Caddyfile: listens on `:{$SERVICE_PORT}`; cache/content-type headers; hides dotfiles.
- Compose: uses `HOST_PORT`/`SERVICE_PORT`; passes `PUBLIC_BASE_URL` consistently.
- CI: conservative release policy; provenance/attestations; SARIF uploads.

### Breaking changes

- **Environment variables:** If you relied on `PORT`, switch to `HOST_PORT` (host mapping) and `SERVICE_PORT` (in-container Caddy). Update `PUBLIC_BASE_URL` to your host/domain.
- **User/permissions:** Container runs as root. Files under `public/` are root-owned on the host. Use `user: "${PUID}:${PGID}"` in compose override if needed.

### Upgrade

1. Pull the new image: `docker pull fnayou/podcastify:1.0.1`
2. Update `.env` to use `HOST_PORT` + `SERVICE_PORT` (see [deployment docs](docs/deployment.md#environment-variables))
3. Ensure `public/` and `podcasts/` dirs are writable: `chmod -R a+rwX public podcasts`
4. Recreate: `docker compose down && docker compose up -d --pull always`
5. Generate on demand (optional): `docker compose exec podcastify python /app/app.py generate`

### Known limitations

- Root-owned files on the host. Use `sudo` to manage or `user: "${PUID}:${PGID}"` in compose override.
- NAS/NFS with restricted writes: ensure exported paths are writable; mount as `:rw`. SELinux users may need `:Z`.

### Image

Multi-arch: `linux/amd64`, `linux/arm64`. SBOM and provenance attached to release build. `latest` moves only on stable tags.

---

For previous releases, see [GitHub Releases](https://github.com/fnayou/podcastify/releases).

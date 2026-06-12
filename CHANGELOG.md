# Changelog

All notable changes to Podcastify are documented here. See [GitHub Releases](https://github.com/fnayou/podcastify/releases) for artifacts and SBOM/provenance.

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

# Podcastify audit: DOCS

Scope: README.md, docs/*.md, CHANGELOG.md, AGENTS.md, CLAUDE.md, docs/agents/, GLOSSARY.md, docs/adr/, templates/, .editorconfig, LICENSE, .gitignore, .env.example, .dockerignore, root layout. Checked against podcastify/*.py, docker/podcastify/*, docker-compose.yml, tasks/*.yml, Taskfile.yml, .github/workflows/*, git tags and history. Read-only. No tests, no docker, no network from Bash. One WebFetch of GitHub docs (CONTRIBUTING placement).

Line numbers are from the files as they are on `main` at HEAD `963a220`.

---

### DOCS-01 README still teaches the retired PORT variable
- severity: high
- evidence:
  - `README.md:62` `- "${HOST_PORT:-8080}:${PORT:-8080}"`
  - `README.md:64` `- PORT=${PORT:-8080}`
  - `README.md:128` `PORT=8080`
  - `README.md:35` "Caddy listens on `${PORT}` inside the container."
  - `README.md:154` `:{$PORT} {`
  - `README.md:50` `docker run --rm   -e PORT=8080 ...`
  - truth: `docker/podcastify/Caddyfile:1` `:{$SERVICE_PORT} {`; `docker/podcastify/Dockerfile:44` `ENV SERVICE_PORT=8080 \`; `docs/adr/0002-env-var-contract.md:34` "`PORT` is retired. It must not appear in any tracked file except a one-line migration note."
- problem: The README is the first page users read. Its compose file maps the host port to `${PORT}` but the container's Caddy listens on `SERVICE_PORT` (default 8080). A user who follows `README.md:128` and sets `PORT=9000` gets a published port 9000 that points at container port 9000, where nothing listens. The README also breaks ADR 0002, which bans `PORT` in tracked files. Only `docs/deployment.md` was updated.
- fix: Replace every `PORT` in README with `SERVICE_PORT`. Shorten the README env and compose blocks to link `docs/deployment.md#environment-variables`, or make them match `docker-compose.yml` exactly. Keep one source of truth. Add a grep check in CI for `[^_A-Z]PORT` in docs (see DOCS-03).
- effort: S
- depends-on: none

### DOCS-02 README "Security hardening" snippet breaks the default image
- severity: high
- evidence:
  - `README.md:176` "The image runs fine as-is. ... you can apply these Compose settings ... without changing the image:"
  - `README.md:182-187` `read_only: true` / `tmpfs: - /tmp` / `security_opt: - no-new-privileges:true` / `cap_drop: ["ALL"]` (no `user:` line)
  - `docs/deployment.md:123` "Needs the `CHOWN`, `SETUID` and `SETGID` capabilities, so do not combine it with `cap_drop: ["ALL"]`."
  - `docker/podcastify/entrypoint.sh:17-22` root branch: `RUNAS="su-exec ${PUID}:${PGID}"`
  - `docker/podcastify/entrypoint.sh:40` `exec /sbin/tini -- $RUNAS caddy run ...`
- problem: With the README snippet, the container starts as root (no `user:` pin). The entrypoint then runs `su-exec` to drop to PUID/PGID. With `cap_drop: ["ALL"]`, `su-exec` cannot call setuid/setgid, so the Caddy `exec` on line 40 should fail and the container should exit. I did not run this (no docker), so this is by reading. The README is the page a user copies from, and it contradicts `docs/deployment.md`, which warns against this exact combination. The README also says the app "listens on high port `${PORT}` so none are needed" (`README.md:190`), which is stale (DOCS-01).
- fix: Delete the cap_drop example from README. Replace the section with a one-line link to `docs/deployment.md#security-hardening`, which has the correct hardened variant (`user: "1000:1000"`, `read_only`, `cap_drop`). Verify the hardened variant with `task docker:up` once a ticket runs it.
- effort: S
- depends-on: DOCS-01

### DOCS-03 README drifted from the shipped Caddyfile, env contract and tree
- severity: medium
- evidence:
  - `README.md:151` "uses an environment variable for the port and hides `.gitkeep` from listings"; `README.md:161` `hide .gitkeep`
  - truth: `docker/podcastify/Caddyfile:19` `hide .*`; `Caddyfile:6-15` adds RSS/MP3/image headers that README's example lacks (`README.md:153-169`).
  - `README.md:121-143` env block lists only HOST_PORT, PORT, PUBLIC_BASE_URL, PODCASTS_ROOT, PUBLIC_ROOT, RUN_ON_START, PUBLISH_XML. Missing vs `.env.example:11-23`: `CACHE_ROOT`, `PUID`, `PGID`, `LOG_LEVEL`, `SERVICE_PORT`.
  - `README.md:91` tree comment "Caddyfile # uses :{$PORT} and hides .gitkeep"
  - `README.md:52` and `README.md:60` pin `fnayou/podcastify:v1.0.0`. Repo tags are `1.0.1`, `v1.0.1`, `v1.1.0`, `v1.1.1` (`git tag -l`); no `v1.0.0` tag exists in this repo.
  - The tree at `README.md:84-104` omits the `podcastify/` package, `tests/`, `tasks/`, `templates/` and `docs/`, which are the code and the docs.
- problem: The README is the onboarding page and reads as current. Its Caddy snippet and env list do not match what ships. A reader who copies the Caddyfile loses the `Cache-Control` and MIME headers for MP3s and feeds. A reader who pins `v1.0.0` runs an image two releases behind. The tree hides where the code is.
- fix: Make README a short overview that links to `docs/deployment.md` (env table and Caddyfile are already correct there, see Good). Update the tree to show `podcastify/`, `tasks/`, `templates/`, `docs/`. Pin examples to `v1.1.1` or to `latest`.
- effort: S
- depends-on: DOCS-01

### DOCS-04 runtime.md states CI facts that the workflows do not do
- severity: medium
- evidence:
  - `docs/runtime.md:19` "Container images are built only on tagged releases (`v*.*.*`)."
  - `docs/runtime.md:20` "All releases are scanned by Trivy for CVEs before publishing."
  - truth: `.github/workflows/ci.yml:89-98` builds the image on every PR (`push: false`, `load: true`). `.github/workflows/release.yml:99-106` builds with `push: true`, then `release.yml:118` `name: Trivy scan (push, fail on CRITICAL)` runs after the push.
- problem: The image is pushed to Docker Hub before the scan runs. A CRITICAL finding fails the job but the image is already public. The doc says the opposite. "Built only on tags" is also wrong, since PRs build the image (without pushing it). This is a security claim, so it must be accurate.
- fix: Reword now to "pushed only on tagged releases; scanned after push, job fails on CRITICAL". Later ticket: scan before push (build with `load: true`, scan, then push the same digest) so the sentence can stay true.
- effort: S
- depends-on: none

### DOCS-05 configuration.md has stale or incomplete field claims
- severity: medium
- evidence:
  - `docs/configuration.md:28` `| author-name | string | Yes | Author/creator name. |`
  - truth: `podcastify/parser.py:59` `author_name: Optional[str] = Field(None, alias="author-name")`; `parser.py:60` `author: Optional[str] = None`; `parser.py:77-80` maps legacy `author` when `author-name` is absent.
  - `docs/configuration.md:26` "`name` ... If omitted, derived from the filename." Truth: `podcastify/cli.py:63-68` logs a warning when `name` differs from the filename and then uses the filename.
  - Legacy `author` alias is not documented anywhere in `docs/`.
- problem: Users are told a field is required when it is not, and that `name` controls the identifier when the filename does. Both are reference-doc errors. The channel and episode field lists are otherwise complete against `podcastify/config.py:28-38` (every CHANNEL_FIELDS and EPISODE_FIELDS key is documented), so the fixes are small.
- fix: Change `author-name` to Optional and note the `author` alias. State that the filename is authoritative and `name` only warns on mismatch. Later: generate the field table from the pydantic models (see IDEAS 1) so it cannot drift again.
- effort: S
- depends-on: none

### DOCS-06 architecture-notes.md describes the old duration-cache location
- severity: medium
- evidence:
  - `docs/architecture-notes.md:38-40` "Duration cache: in-memory `_duration_cache` ... persisted to `<PUBLIC_ROOT>/.podcastify-cache.json` (media.py,38). Invalidates on mtime change, but entries for deleted files are never pruned."
  - truth: `podcastify/media.py:22-23` `return Config.CACHE_ROOT / Config.CACHE_FILENAME`; `media.py:58-73` migrates the legacy file; `media.py:86-88` keeps only entries whose file still exists (`if file_path.exists():`).
  - `docs/adr/0003-duration-cache-location.md:4` "Status: Accepted". Its decision is implemented (CACHE_ROOT, pruning, migration).
  - `docs/architecture-notes.md:31` cites `PodcastChannelModel:64`; the `language="en"` default is on `parser.py:65`.
- problem: An AI agent reading architecture-notes (the file AGENTS.md says to read before changing `podcastify/`) will think the cache lives in the served directory and never prunes. Both are false, and the cache location is a security-relevant point (ADR 0003 exists for that reason). `docs/architecture.md` does not mention the cache at all.
- fix: Update architecture-notes lines 38-40 to `CACHE_ROOT` and the actual prune and migration behaviour. Fix the line refs. Add one short cache paragraph to `docs/architecture.md`.
- effort: S
- depends-on: none

### DOCS-07 the scaffold template disables auto-discovery, which the docs do not say
- severity: medium
- evidence:
  - `templates/podcast-config-template.yaml:12-19` `episodes:` with `- file: "ep01.mp3"` and a fixed `pub_date: "2025-01-01T08:00:00Z"`.
  - `podcastify/parser.py:164-165` `if validated and validated.episodes is not None:` uses the explicit list and never scans the folder.
  - `docs/getting-started.md:24-34` "add media under public/myshow/" then "Generate feeds", with no mention of the list.
  - `docs/configuration.md:71` "If you omit the `episodes:` list, Podcastify auto-discovers all `*.mp3` files".
- problem: A user who follows getting-started (`task podcastify:new`, copy more MP3s, generate) gets a feed with only `ep01.mp3`. Other MP3s are silently ignored. The docs promise auto-discovery, and the template turns it off. The fixed 2025 pub_date also sorts every new episode with a made-up date when they add one.
- fix: Remove the `episodes:` block from the template (auto-discovery is then the default, which matches the docs), or add a comment and a getting-started sentence that says the list disables auto-discovery. Pick one. Removing the block is the smaller change.
- effort: S
- depends-on: none

### DOCS-08 troubleshooting misses the messages the code actually logs
- severity: medium
- evidence:
  - `docs/troubleshooting.md:13-17` "No episodes found for <name>" with cause "`public/<name>/` directory is missing or empty."
  - truth: `podcastify/cli.py:70-74` logs `Public directory missing for {podcast_name}` and returns before the "No episodes" check on `cli.py:80`.
  - `cli.py:49` "Empty or invalid config for {podcast_name}"; `cli.py:55` "Config validation failed for {podcast_name}: {err}" (for example `parser.py:86` "type must be 'episodic' or 'serial'").
  - `docker/podcastify/entrypoint.sh:21` "Could not chown data dirs; continuing (check bind-mount perms)".
  - `docker/podcastify/entrypoint.sh:31` "Generator exited non-zero; continuing to serve existing content".
  - `podcastify/parser.py:200` "Image file not found".
  - CHANGELOG v1.0.1 "Known limitations" names NAS/NFS permission problems as the main issue. The troubleshooting page has no permission section.
- problem: Users search for the exact log text. Four of the most common failures (missing public dir, invalid config, permission/chown warnings, generator failure at boot) have no entry. The permission case is the one the project has been fighting since v1.0.1.
- fix: Add entries for these messages. For permissions, point to `PUID`/`PGID` and `task docker:fix:perms` (`tasks/docker.yml`). Fix the "No episodes" cause so it matches the code.
- effort: S
- depends-on: none

### DOCS-09 CHANGELOG has a missing release section and an undocumented cache move
- severity: medium
- evidence:
  - `git tag -l` lists `1.0.1`, `v1.0.1`, `v1.1.0`, `v1.1.1`. `CHANGELOG.md` has sections for `## v1.1.1` (line 5) and `## v1.0.1` (line 34) only.
  - `.github/workflows/release.yml:169-176` extracts the notes by the `## <tag>` header. For `v1.1.0` the body falls back to "See CHANGELOG.md for details." (`release.yml:178-180`).
  - `git grep -c CACHE_ROOT v1.1.1 -- podcastify docker` finds `CACHE_ROOT` in `v1.1.1` (`media.py`, `config.py`, `Dockerfile`). `CHANGELOG.md:19-32` (v1.1.1 "Changed") does not mention it. Users must now mount `./cache` for `read_only` (`docs/deployment.md:139`), and the old cache file is migrated from `public/` (`media.py:58-73`).
  - No upgrade steps exist for v1.1.x. The only upgrade section is v1.0.1 (`CHANGELOG.md:71-77`).
  - A lightweight tag `1.0.1` sits beside `v1.0.1`. The release workflow only matches `v*.*.*`, so `1.0.1` is ignored, but it is confusing.
- problem: The v1.1.0 release page has no notes. A user upgrading to v1.1.1 is not told that the cache moved, that `read_only` needs a `cache` volume, or that the old cache file is migrated. The stray tag adds noise.
- fix: Add a `## v1.1.0` section (from the commits, or "Initial release notes not recovered" if needed). Add the CACHE_ROOT migration and volume note to v1.1.1. Add an "Upgrade" line per release that changes env or volumes. Delete the stray `1.0.1` tag only after the owner confirms (tag deletion is outward-facing, so ask first).
- effort: S
- depends-on: none

### DOCS-10 no Dependabot or Renovate config for pinned dependencies and base images
- severity: medium
- evidence:
  - `requirements.txt:1-2` `PyYAML==6.0.2`, `pydantic==2.11.5`; `requirements-dev.txt:1-4` pins pytest, pytest-cov, pytest-mock, pre-commit.
  - `docker/podcastify/Dockerfile:4` `FROM caddy:2.11.4-alpine AS caddy`; `Dockerfile:6` `FROM python:3.12-alpine3.22`.
  - `.github/workflows/ci.yml:21` `uses: actions/checkout@v4`; `ci.yml:141` `aquasecurity/trivy-action@v0.36.0`.
  - No `.github/dependabot.yml` or `renovate.json` exists (`git ls-files` shows no such file).
  - `docs/runtime.md:9` "our Dockerfile rebuilds are infrequent (only on explicit rebuilds)".
- problem: Every pin is manual. Nothing tells the owner that pydantic, Caddy, the Python base or the Actions have new versions or CVEs. `docs/runtime.md` accepts this trade-off, but without a bot the base images get refreshed only when someone remembers.
- fix: Add one `.github/dependabot.yml` with three ecosystems: `pip` (root), `docker` (`/docker/podcastify`), `github-actions`. This is lighter than Renovate and covers the same ground for this repo. Note in `docs/runtime.md` that Dependabot opens the bump PRs.
- effort: S
- depends-on: none

### DOCS-11 getting-started points to an env section that is not there
- severity: low
- evidence:
  - `docs/getting-started.md:15` "# create .env from the section above (set HOST_PORT if you want a custom port)"
  - `docs/getting-started.md` has no env section. The "section above" exists only in `README.md:121-143`.
  - `.env.example` exists (repo root) and is not linked from any doc (`grep` of docs finds no reference).
- problem: A new user who opens getting-started first reads "the section above" and finds nothing. The correct file, `.env.example`, is not mentioned.
- fix: Replace the line with "copy `.env.example` to `.env` and set `HOST_PORT` if needed, see `deployment.md#environment-variables`."
- effort: S
- depends-on: DOCS-03

### DOCS-12 .gitignore does not cover the new cache directory
- severity: low
- evidence:
  - `.gitignore:23-24` "# Duration cache (local)" / `.podcastify-cache.json`
  - `docs/deployment.md:43` `- ./cache:/app/.cache`; `docker-compose.yml:29` `- ./cache:/app/.cache:rw`
  - `git grep -n cache -- .gitignore` finds only the root-level filename line (`.gitignore:24`). No `cache/` pattern.
- problem: After the CACHE_ROOT move (ADR 0003), the cache file is written to `./cache/.podcastify-cache.json`. The rule at `.gitignore:24` matches only the repo-root path, so `git add .` can commit the cache file (it contains absolute paths and mtimes of the user's media).
- fix: Add `cache/` (and keep the old filename line) to `.gitignore`. Add `cache/` to `.dockerignore` as well, so the build context stays clean.
- effort: S
- depends-on: none

### DOCS-13 ADR quality: broken refs, stale line refs, no index, unlinked supersession
- severity: low
- evidence:
  - `docs/adr/0001-root-only-container-runtime.md:5` "Superseded. ... see `docs/runtime.md`." and `:31` `RELEASE_NOTES_v1.0.1.md`
  - `docs/adr/0002-env-var-contract.md:55` `RELEASE_NOTES_v1.0.1.md`. The file is not tracked (`git ls-files` shows no such file).
  - `docs/adr/0002-env-var-contract.md:53` `docker/podcastify/Dockerfile:23-28`; the ENV block is now at `Dockerfile:44-57`.
  - `docs/adr/0003-duration-cache-location.md:10` `podcastify/media.py:16-17`; the cache path is now `media.py:22-23`.
  - ADR 0001 is "Superseded" but the replacement is a runbook (`docs/runtime.md`), not an ADR, so the decision trail has no successor record.
  - No `docs/adr/README.md` index and no template.
  - Numbering is sequential (0001-0003), and the content of 0002 is clear. This is the good part.
- problem: Dead references and wrong line numbers erode trust in the decision log. A superseded ADR without a successor makes the runtime decision hard to find. These are small problems, but the ADR set is three files, so they are easy to fix.
- fix: Remove the RELEASE_NOTES references or add the file. Replace line refs with symbol names (for example `Dockerfile` ENV block) so they do not rot. Add a three-line `docs/adr/README.md` index. Write a short ADR 0004 for the runtime choice (tini, PUID/PGID, no pinned apk) if the owner wants that decision recorded.
- effort: S
- depends-on: DOCS-01 (ADR 0002 bans PORT in tracked files; see DOCS-01)

### DOCS-14 no SECURITY.md for a public image with a public reporting path
- severity: low
- evidence:
  - `git ls-files` shows no `SECURITY.md`, `.github/SECURITY.md` or `docs/SECURITY.md`.
  - The project publishes a public image (`README.md:41`, `.github/workflows/release.yml:150` attestation to docker.io) and ships a hardening section (`docs/deployment.md:119-137`).
- problem: A reporter who finds a vulnerability has no documented route. Opening a public issue is the default.
- fix: Add a 10-line `SECURITY.md` at the repo root that says which versions are supported (latest tag only) and asks for private reports through GitHub's private vulnerability reporting. Enable that feature in repo settings. Skip CODE_OF_CONDUCT and CODEOWNERS, they add weight without value here.
- effort: S
- depends-on: none

### DOCS-15 no issue or PR templates, although the docs ask for their content
- severity: low
- evidence:
  - `docs/contributing.md:90-96` "Reporting Bugs ... Include: Podcastify version or image tag, Docker/Task version, Minimal config to reproduce, Relevant log output"
  - `docs/contributing.md:84-88` PR steps: branch, change, `task dev:validate`, commit, open PR titled in Conventional Commits form.
  - `.github/` contains only `workflows/`. No `ISSUE_TEMPLATE/` and no `PULL_REQUEST_TEMPLATE.md`.
- problem: The bug-report checklist lives only in prose, so reports arrive without versions or logs. The PR checklist (`task dev:validate`, Conventional Commits title, CHANGELOG entry for user-visible changes) is also prose only.
- fix: Add `.github/ISSUE_TEMPLATE/bug_report.md` with the four fields from contributing.md, and `.github/PULL_REQUEST_TEMPLATE.md` with three checkboxes (validate run, title format, CHANGELOG entry if user-visible). Two short files, no tooling.
- effort: S
- depends-on: none

### DOCS-16 deployment reverse-proxy example points at the host port, not the container port
- severity: low
- evidence:
  - `docs/deployment.md:28` `- "${HOST_PORT:-8080}:${SERVICE_PORT:-8080}"`
  - `docs/deployment.md:91-94` "Set `PUBLIC_BASE_URL=https://podcasts.domain.tld` ... Forward to the container's `${SERVICE_PORT}` (default 8080)"
  - `docs/deployment.md:100` `reverse_proxy localhost:8080`
- problem: The text says to forward to the container port, but the example uses `localhost:8080`, which is the host port when `HOST_PORT` is changed. A user with `HOST_PORT=1234` who copies the example gets a proxy to a host port nothing listens on. The example and the text disagree.
- fix: Change the example to `reverse_proxy localhost:${HOST_PORT}` with a note that `HOST_PORT` is the published port, or say explicitly "the host port (`HOST_PORT`)".
- effort: S
- depends-on: none

---

## IDEAS

Feasibility only. These are not findings.

1. Generated documentation website
   - Stack: MkDocs Material (Python, fits requirements-dev; one `mkdocs.yml` and the existing `docs/*.md`). Hugo if the owner wants no Python dependency.
   - Hosting: GitHub Pages from a Pages workflow (free for this public repo).
   - Depends on: relative links in `docs/` (they work), a fix for the drift in DOCS-01 to DOCS-06 first, and ideally a config reference generated from `PodcastChannelModel.model_json_schema()` and `Config.CHANNEL_FIELDS` so the reference cannot drift again.
   - Note: `docs/adr/` and `docs/agents/` should be excluded from the public site.

2. Minimalist site to serve feeds and files instead of the Caddy browser
   - Lightest option: have `cli.py` write `public/index.html` after publish (a Python string template, no new dependency). Caddy keeps serving `/app/public`.
   - Caddy change: drop `browse` in `docker/podcastify/Caddyfile:17-20`, keep `hide .*`.
   - Depends on: `cli.py:123-143` (atomic write point), `clean:feeds` only removes `*.xml` (`tasks/podcastify.yml:73-74`), and the healthcheck hits `/` (`Dockerfile:61`), so the page must return 200.
   - Hosting: same container, no change to the compose file.

3. One-page marketing site for the application
   - Stack: one static HTML file with inline CSS (no build), or Astro/Eleventy only if more pages come.
   - Hosting: GitHub Pages or Cloudflare Pages (free tier). Prefer a separate repo or `site/` folder, so it does not touch the release flow.
   - Depends on: README copy (`README.md:8` tagline, `README.md:10-12` links). Needs a domain decision. No runtime dependency on the app.
   - Keep it separate from `docs/`, since GitHub Pages "/docs" source would publish the internal ADRs.

---

## Summary

| ID | Severity | Effort | Depends-on |
|---|---|---|---|
| DOCS-01 | high | S | none |
| DOCS-02 | high | S | DOCS-01 |
| DOCS-03 | medium | S | DOCS-01 |
| DOCS-04 | medium | S | none |
| DOCS-05 | medium | S | none |
| DOCS-06 | medium | S | none |
| DOCS-07 | medium | S | none |
| DOCS-08 | medium | S | none |
| DOCS-09 | medium | S | none |
| DOCS-10 | medium | S | none |
| DOCS-11 | low | S | DOCS-03 |
| DOCS-12 | low | S | none |
| DOCS-13 | low | S | DOCS-01 |
| DOCS-14 | low | S | none |
| DOCS-15 | low | S | none |
| DOCS-16 | low | S | none |

All 16 findings are S effort. Start with DOCS-01 and DOCS-02: they are the copy-paste paths most likely to break a new user.

### Already good (no ticket)

- `docs/deployment.md` env table, shipped Caddyfile snippet (`hide .*`) and hardened section match `docker/podcastify/Caddyfile:19`, `entrypoint.sh` and `.env.example`.
- `docs/configuration.md` covers every key in `Config.CHANNEL_FIELDS` and `Config.EPISODE_FIELDS` (`podcastify/config.py:28-38`). Only the legacy `author` alias is missing (DOCS-05).
- `GLOSSARY.md` matches `podcastify/config.py` (CACHE_ROOT, `Config.BASE_URL` reads `PUBLIC_BASE_URL`, LOG_LEVEL, PUBLISH_XML).
- `docs/adr/0002-env-var-contract.md` sets a clear contract. ADR numbering is sequential.
- `AGENTS.md` and `CLAUDE.md` are coherent: CLAUDE imports AGENTS and adds only the agent-skill config, whose referenced files (`docs/agents/*.md`, `GLOSSARY.md`, `docs/adr/`) exist.
- Conventional Commits rule is the same in AGENTS.md, `docs/contributing.md:68-70`, `commits.yml:14` and `.pre-commit-config.yaml` types.
- Taskfile commands listed in README and AGENTS (`docker:*`, `podcastify:*`, `dev:*`, `doctor`) exist in `tasks/` and `Taskfile.yml`.
- README links to `docs/*.md` all resolve. `LICENSE` is MIT and present.
- `docs/contributing.md` is a valid contributing location: GitHub accepts CONTRIBUTING in root, `docs/` or `.github/`, case-insensitive (checked against GitHub docs). No root CONTRIBUTING.md is needed.
- No CODEOWNERS: not needed for a single-owner repo.
- `.editorconfig` is minimal and correct (LF, UTF-8, 4-space Python, 2-space YAML). `.dockerignore` excludes `public/*`, `podcasts/*` and `.env`.
- `.gitignore` ignores `.env` but keeps `.env.example`.


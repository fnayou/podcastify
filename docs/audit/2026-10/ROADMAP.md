# Podcastify roadmap (draft from the 2026-10 audit)

Sources: core.md (22 findings), docker.md (18), cicd.md (24), docs.md (16) in this folder. 80 findings merged into 38 tickets plus 3 site epics.
Size: S under 1h, M half day, L more. Labels: track + size. `blocked-by` becomes GitHub native dependencies.

## Tracks and tickets

### docs
| id | title | from | size | blocked-by |
|---|---|---|---|---|
| T01 | Sync README with the shipped image: SERVICE_PORT, real Caddyfile, env list, hardening with `user:`, tree, version pins; fix getting-started env pointer | DOCKER-01, DOCS-01/02/03/11 | S | none |
| T02 | Fix configuration.md (author-name optional, legacy author, name vs filename); drop `episodes:` from the scaffold template or document the switch | DOCS-05/07 | S | none |
| T03 | Troubleshooting: add real log messages, permissions section; fix reverse-proxy example to use HOST_PORT | DOCS-08/16 | S | none |
| T04 | Refresh architecture-notes, runtime.md, ADRs (cache path, pruning, Trivy order, supervisord leftovers, stale refs, dead RELEASE_NOTES links); add ADR 0004 PUID/PGID runtime and an ADR index | CORE-14 docs, DOCKER-13/14, DOCS-04/06/13 | M | T22 (final wording), T36 (Trivy order) |
| T05 | SECURITY.md, enable private vulnerability reporting, issue and PR templates | DOCS-14/15 | S | none |

### core
| id | title | from | size | blocked-by |
|---|---|---|---|---|
| T10 | Make feed XML always well-formed: escape `]]>` in CDATA, strip illegal control characters | CORE-01 | S | none |
| T11 | Percent-encode enclosure and image URLs; normalise PUBLIC_BASE_URL (trailing slash, scheme check) | CORE-02/03 | S | none |
| T12 | Skip and report episodes whose file is missing (no length=0, no 1970 pubDate) | CORE-04 | S | none |
| T13 | Degrade gracefully when ffprobe is missing (one warning, durations omitted) | CORE-05, DOCKER-08 | S | none |
| T14 | Spike and decide: replace ffmpeg/ffprobe with a pure-Python MP3 reader (tinytag) to shrink image and CVE surface | DOCKER-07 | M | T13 |
| T15 | Parse pub_date once in the model: accept unquoted YAML dates, UTC for naive values, one `published` field for sort and render | CORE-06/07 | S | none |
| T16 | Enclosure MIME map and case-insensitive scan, or reject non-MP3 at validation | CORE-08 | S | none |
| T17 | Feed spec conformance: xmlns:content, atom self link, itunes:explicit true/false, no empty tags (verify against Apple page first) | CORE-09 | S | T22 |
| T18 | Reject duplicate GUIDs, duplicate files, colliding names and .yaml/.yml twins; allow-list podcast names and filenames | CORE-10/11 | S | none |
| T19 | CLI exit codes (0 ok, 1 any failed, 2 usage), argparse with `generate` and `--dry-run`; empty install exits 0 | CORE-12, DOCKER-15 | S | none |
| T20 | Logging: one configure call in main, tracebacks via logger.exception, shared bool parser for env and YAML | CORE-13/18 | S | none |
| T21 | Cache robustness: do not persist timeouts, one entry per path; hidden temp file, fsync, stale temp cleanup | CORE-16/17 | S | none |
| T22 | Render from typed models with xml.etree (no dict round trip, no string concatenation); `extra=forbid` for typos | CORE-15 | M | T10, T11, T15 |
| T23 | Remove dead code: extract_podcast_metadata, EPISODE_FIELDS, app.py re-exports, private `__all__` | CORE-14 code | S | none |

### test
| id | title | from | size | blocked-by |
|---|---|---|---|---|
| T24 | Isolate tests: tmp PUBLIC/PODCASTS/CACHE roots, reset MediaProcessor state per test, mock ffprobe | CORE-20, CORE-05 | S | T13 |
| T25 | Real golden XML test: snapshot files, injected clock, parse with ElementTree, nasty-input case | CORE-19 | S | T10, T11, T24 |
| T26 | Edge-case tests per fix; branch coverage in the gate; assert specific log messages | CORE-21 | M | T10, T11, T12, T15, T18, T24 |

### docker
| id | title | from | size | blocked-by |
|---|---|---|---|---|
| T28 | Remove Caddy `browse`; add `/healthz`, quiet its log, healthcheck start-period | DOCKER-02/10 | S | none (ship as one change) |
| T29 | Caddy hardening: admin off, nosniff, drop Server, MP3 cache policy without `immutable` | DOCKER-11/12 | S | none |
| T30 | Entrypoint: tini as real PID 1, chown only what the app writes, lower-case RUN_ON_START, show chown errors | DOCKER-03/09/15 | S | none |
| T31 | On-demand `generate` runs as PUID/PGID (entrypoint subcommand); update tasks and docs | DOCKER-04 | S | T30 |
| T32 | Path env vars: remove PUBLIC/PODCASTS/CACHE_ROOT from compose and docs (recommended) or honour them everywhere | DOCKER-06 | S | none |
| T33 | Compose cleanup: drop duplicated defaults, show 127.0.0.1 binding for proxy users | DOCKER-18 | S | T32 |
| T34 | Auto-regenerate in the container (GENERATE_INTERVAL, fingerprint poll, no rewrite when content unchanged) | DOCKER-05 | M | T19, T21, T30 |
| T35 | Smoke test in CI: start the built image, poll /healthz, make `dev:smoke` robust | CICD-19 | M | T28 |

### ci-release
| id | title | from | size | blocked-by |
|---|---|---|---|---|
| T06 | Dependabot: pip, docker, github-actions, pre-commit; weekly, grouped | CICD-06, DOCS-10, DOCKER-16 | S | none |
| T07 | Pin all third-party actions by SHA, least-privilege permissions, remove dead CI config (QEMU, unused tags, REGISTRY, build-args) | CICD-01/02/09 | S | none |
| T36 | Scan before push, one scanner (Trivy or Grype), drop Docker Scout and duplicate SARIF, weekly rescan of latest | CICD-03/04/05/07 | M | T07 |
| T37 | Reusable test workflow; CI also on push to main; one concurrency policy; pyproject-driven pytest and coverage | CICD-08/10/11 | M | none |
| T27 | pyproject.toml, ruff and hadolint in pre-commit and CI | CICD-18 | S | T37 |
| T38 | Epic: CalVer and git-cliff. Children: ADR for version scheme, cliff.toml and notes step, tag policy (X.Y.Z + latest), single provenance, Docker Hub description sync, v1.1.0 changelog backfill, retag v1.1.x, delete stray 1.0.1 | CICD-12/13/14/15/16, DOCS-09 | L | T07, T36 |

### dx
| id | title | from | size | blocked-by |
|---|---|---|---|---|
| T09 | Taskfile cleanup: dev:setup venv, remove prune from docker:clean, fix docker:pull, merge info/health/version/env, drop dead dev:test:ci | CICD-20/21/22/23 | S | none |
| T39 | .gitignore and .dockerignore: cache/, venv, caches; allow-list build context | DOCKER-17, DOCS-12 | S | none |

### security
| id | title | from | size | blocked-by |
|---|---|---|---|---|
| T40 | Refresh dependencies (pydantic, pytest, PyYAML) and pin transitives; run the suite | CORE-22, CICD-06 | S | T06 |
| T41 | One-time baseline vulnerability scan of the built image and dependencies; record result | pending approval | S | none |

### site epics (after the baseline, not scheduled)
- E1 docs website (MkDocs Material, GitHub Pages; generate config reference from the pydantic models). Blocked by T01 to T04.
- E2 generated minimalist index site served by Caddy, replacing `browse`. Blocked by T28, T21.
- E3 one-page marketing site, separate from docs. Independent.

## Waves
1. Stop the bleeding: T01, T10, T11, T12, T28, T39, T07, T06, T05
2. Foundations: T13, T24, T37, T15, T18, T19, T20, T29, T30, T32, T09, T23, T36, T40
3. Structural: T22, T17, T25, T26, T27, T31, T33, T34, T35, T04, T02, T03
4. Decide and migrate: T14 spike, T38 epic
5. Sites: E1, E2, E3

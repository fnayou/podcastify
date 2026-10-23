# Podcastify

Tiny self-hosted podcast RSS generator. Drop MP3s into a folder, add a YAML config, get iTunes-compatible RSS feeds. One Docker container (Caddy + Python).

- Repository: https://github.com/fnayou/podcastify
- Docker Hub: https://hub.docker.com/r/fnayou/podcastify
- License: MIT

## Stack

Python 3.12 (`podcastify/` package, thin `app.py` entry), PyYAML, pydantic, Caddy (static server), tini (PID 1), Docker Compose, Taskfile (go-task).

## Layout

```
app.py                  # CLI entry point
podcastify/             # config, parser, media, rss, cli, logging_config
docker/podcastify/      # Dockerfile, Caddyfile, entrypoint.sh
podcasts/               # YAML configs: <name>-podcast.yaml
public/                 # media in <name>/, feeds in <name>.xml
templates/              # podcast config scaffold used by `task podcastify:new`
tests/                  # pytest suite
tasks/                  # Taskfile includes (dev, docker, podcastify)
docs/                   # human docs; docs/adr/ decisions; docs/agents/ skill config
GLOSSARY.md             # domain vocabulary
```

## Commands

```bash
task docker:up                  # build and start container
task docker:down                # stop and remove
task docker:logs                # follow logs
task podcastify:generate        # run RSS generator
task podcastify:new NAME=myshow # scaffold a podcast config
task podcastify:clean:feeds     # remove generated XML
task doctor                     # check environment
task dev:test:coverage          # tests with 90% coverage gate
task dev:validate               # tests + Docker build, mirrors CI
```

## Architecture

| Class | Module | Responsibility |
|---|---|---|
| `Config` | `config.py` | env vars and field whitelists |
| `MediaProcessor` | `media.py` | ffprobe duration, persistent cache |
| `ConfigurationManager`, `EpisodeManager` | `parser.py` | YAML load/validate, episode discovery |
| `RSSGenerator` | `rss.py` | iTunes RSS XML |
| `PodcastProcessor` | `cli.py` | load, validate, generate, atomic write |

Invariants and gotchas: `docs/architecture-notes.md`. Runtime and container: `docs/runtime.md`.

## Rules

- Python: 4-space indent, UTF-8, LF. YAML: 2-space indent. See `.editorconfig`.
- Class-based; PascalCase classes, snake_case functions. Logic lives in `podcastify/`; `app.py` stays thin.
- No comments unless requested. No unused imports or dead code.
- No secrets or credentials in commits.
- Episode GUID defaults to SHA-1 of `<podcast>/<filename>`; renaming breaks subscriber history.
- Config files are `podcasts/<name>-podcast.yaml`; media in `public/<name>/`; feeds in `public/<name>.xml`.
- Docker-first: build and run through `task docker:*`.

## Testing

- `pytest` + `pytest-mock`; tests in `tests/`, one file per class or module; fixtures in `tests/conftest.py`.
- All new code has tests. Coverage of `podcastify/` stays at or above 90%.
- Before finishing a change, run `task dev:validate` (CI parity: tests plus Docker build).

## Git

- Conventional Commits, enforced three ways: the `commit-msg` hook (`task dev:hooks` installs it), the `commits` CI check on every PR (title and each commit subject), and review. Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. `!` or a `BREAKING CHANGE:` footer marks a breaking change. No emojis.
- `main` is protected: changes land only through a PR with the `test`, `docker` and `commits` checks green. No force-push, no deletion, linear history.
- PRs merge by rebase only, so each commit lands on `main` as written. Keep commits clean before opening the PR.
- Branch from `main`: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`.
- Releases: tag `vX.Y.Z` on `main`; `release.yml` builds, scans, pushes the image and creates the GitHub Release from the matching `CHANGELOG.md` section.
- Never commit, push, tag or rebase unless asked.

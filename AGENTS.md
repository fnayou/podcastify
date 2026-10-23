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
task release:changelog          # preview the release notes (git-cliff in a container)
task worktree:install           # install or re-assert worktree lane tooling
task worktree:verify            # check lane tooling and the merge refusals
```

## Architecture

| Class | Module | Responsibility |
|---|---|---|
| `Config` | `config.py` | env vars and media types |
| `MediaProcessor` | `media.py` | tinytag duration, persistent cache |
| `ConfigurationManager`, `EpisodeManager` | `parser.py` | YAML load/validate, episode discovery |
| `RSSGenerator` | `rss.py` | iTunes RSS XML |
| `PodcastProcessor` | `cli.py` | load, validate, generate, atomic write |

Invariants and gotchas: `docs/architecture-notes.md`. Runtime and container: `docs/runtime.md`.

## Rules

- Python: 4-space indent, UTF-8, LF. YAML: 2-space indent. See `.editorconfig`.
- Class-based; PascalCase classes, snake_case functions. Logic lives in `podcastify/`; `app.py` stays thin.
- Comments only to explain why: a constraint, a trade-off or a non-obvious choice. Never narrate what the code does. A short module docstring is fine for a tool script.
- No unused imports or dead code.
- No secrets or credentials in commits.
- Episode GUID defaults to SHA-1 of `<podcast>/<filename>`; renaming breaks subscriber history.
- Config files are `podcasts/<name>-podcast.yaml`; media in `public/<name>/`; feeds in `public/<name>.xml`.
- Docker-first: build and run through `task docker:*`.

## Testing

- `pytest` + `pytest-mock`; tests in `tests/`, one file per class or module; fixtures in `tests/conftest.py`.
- All new code has tests. Coverage of `podcastify/` stays at or above 90%.
- Before finishing a change, run `task dev:validate` (CI parity: tests plus Docker build).

## Worktree lanes

Parallel work runs in git worktrees ("lanes"), each opened as a herdr workspace through worktrunk and the pinned herdr-worktrunk plugin. Guide: [docs/worktree-lanes.md](docs/worktree-lanes.md). Lane contract:

- Create lanes from the primary checkout with worktrunk. The gitignored files listed in `.worktreeinclude` (`.env`) are copied into a new lane.
- Shared resource: the host port. Compose project names come from the directory, so containers, networks and bind mounts are per lane. Give each lane its own `HOST_PORT` in its `.env`. The lane that keeps 8080 is the resource owner; stop its containers (`task docker:down`) before another lane takes 8080. A claim moves nothing else and authorizes no rebuild.
- Never commit or merge through worktrunk. Commit with git; merges happen on GitHub as a rebase merge. Worktrunk hooks refuse the local forms (`.config/wt.toml`).
- A lane is a concurrency boundary, not a credential sandbox.
- One writing agent per lane. Removing a lane, its branch or its workspace needs explicit operator authorization.
- Setup and checks: `task worktree:install`, `task worktree:verify`.

## Git

- Conventional Commits, enforced three ways: the `commit-msg` hook (`task dev:hooks` installs it), the `commits` CI check on every PR (title and each commit subject), and review. Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. `!` or a `BREAKING CHANGE:` footer marks a breaking change. No emojis.
- `main` is protected: changes land only through a PR with the `test`, `docker` and `commits` checks green. No force-push, no deletion, linear history.
- PRs merge by rebase only, so each commit lands on `main` as written. Keep commits clean before opening the PR.
- Branch from `main`: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`.
- Releases: tag `vYYYY.M.PATCH` on `main` (ADR 0007); `release.yml` builds, scans, pushes the image and creates the GitHub Release. The notes come from git-cliff (`cliff.toml`) over the Conventional Commits; `CHANGELOG.md` is frozen history. Preview them with `task release:changelog`.
- Never commit, push, tag or rebase unless asked.

# Contributing

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/fnayou/podcastify
   cd podcastify
   ```

2. Install Task (go-task):
   ```bash
   # macOS
   brew install go-task

   # Linux
   sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d
   ```

3. Check the environment, then create the virtualenv, install the requirements and the commit hook:
   ```bash
   task doctor
   task dev:setup
   ```

   `task dev:setup` creates `.venv`, installs `requirements.txt` and `requirements-dev.txt` into it, and runs `task dev:hooks`. The test tasks use `.venv/bin/python` when it exists.

Tasks that only you need can go in a `Taskfile.dev.yml` at the repository root. It is optional, git-ignored, and its tasks appear under the `devlocal:` prefix.

## Workflow

### Parallel work

Several tickets in parallel use worktree lanes: `task worktree:install` once, then see [worktree lanes](worktree-lanes.md).

### Build and test locally

```bash
# Start the container
task docker:up

# Generate feeds
task podcastify:generate

# View logs
task docker:logs
```

### Add a new podcast for testing

```bash
task podcastify:new NAME=testshow
# place MP3s in public/testshow/
task podcastify:generate
```

### Clean up

```bash
task docker:down
task podcastify:clean:feeds
task docker:clean
```

`task docker:clean` removes only this project's containers, networks and volumes. `task docker:pull` rebuilds the image with freshly pulled base images.

## Code Style

- Python: 4-space indent, UTF-8, LF line endings
- YAML: 2-space indent
- `podcastify/` package with thin `app.py` entry point
- PascalCase for classes, snake_case for functions
- No unused imports or dead code

`ruff` lints and formats Python (config in `pyproject.toml`), and `hadolint` lints the Dockerfile. Both run as pre-commit hooks (`task dev:hooks`) and in the CI `test` job. To check everything at once: `.venv/bin/pre-commit run --all-files`. The hadolint hook needs Docker.

## Commit Conventions

[Conventional Commits](https://www.conventionalcommits.org/): `<type>[scope][!]: <description>`.

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. Mark breaking changes with `!` or a `BREAKING CHANGE:` footer.

```
feat(rss): add season/episode numbering support
fix(parser): resolve image URL when using absolute paths
docs: update deployment guide with nginx example
```

The `commit-msg` hook checks this locally (`task dev:hooks`). The `commits` CI check validates the PR title and every commit subject.

## Pull Requests

`main` is protected: no direct pushes, no force-push, linear history. A PR needs the `test`, `docker` and `commits` checks green, and merges by rebase only.

1. Create a branch from `main`: `git checkout -b feat/my-feature`
2. Make your changes
3. Run `task dev:validate`
4. Commit with the conventional format
5. Push and open a PR titled in the same format

## CI time budget

CI execution time is a requirement. A PR must not push any workflow past its budget. Every PR that touches `.github/workflows/` reports the job durations before and after the change in its description.

| Scope | Baseline (median) | Budget |
|---|---|---|
| CI `test` job | 24 s | 60 s |
| CI `docker` job | 2 min 07 s | 3 min |
| PR total (CI wall time, `test` start to `docker` end) | 2 min 32 s | 4 min |
| Release (all jobs, wall time) | 3 min 46 s | 6 min |

Baseline measured on 2026-10-23 with `gh`: median of the last 8 successful CI runs on PRs to `main` (`test` 11 to 45 s, `docker` 1 min 44 s to 2 min 31 s), and the last release run, `v1.1.1` (`test` 35 s, `docker` 3 min 01 s, `release` 4 s).

To see the durations of the latest runs:

```bash
task ci:durations           # last 5 successful CI and Release runs
task ci:durations LIMIT=8
```

## Reporting Bugs

Include:
- Podcastify version or image tag
- Docker/Task version
- Minimal config to reproduce
- Relevant log output

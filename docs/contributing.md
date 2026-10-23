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

3. Verify environment and install the commit hook:
   ```bash
   task doctor
   pip install -r requirements-dev.txt
   task dev:hooks
   ```

## Workflow

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

## Code Style

- Python: 4-space indent, UTF-8, LF line endings
- YAML: 2-space indent
- `podcastify/` package with thin `app.py` entry point
- PascalCase for classes, snake_case for functions
- No unused imports or dead code

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

## Reporting Bugs

Include:
- Podcastify version or image tag
- Docker/Task version
- Minimal config to reproduce
- Relevant log output

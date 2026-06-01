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

3. Verify environment:
   ```bash
   task doctor
   ```

4. Optional — OpenCode for AI-assisted development:
   ```bash
   cp .env.example .env   # sets OPENCODE_CONFIG=.opencode/opencode.json
   ```
   Slash commands: `/pr`, `/review`, `/release`, `/validate-changes` (see [AGENTS.md](../AGENTS.md#slash-commands)).

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

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — New feature
- `fix:` — Bug fix
- `chore:` — Maintenance, deps, tooling
- `docs:` — Documentation changes
- `refactor:` — Code refactoring
- `test:` — Tests

Examples:
```
feat: add season/episode numbering support
fix: resolve image URL when using absolute paths
docs: update deployment guide with nginx example
```

## Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Ensure `task doctor` passes
5. Commit with conventional commit format
6. Push and open a PR

## Reporting Bugs

Include:
- Podcastify version or image tag
- Docker/Task version
- Minimal config to reproduce
- Relevant log output

# Taskfile Refactor

## Feature
Refactor the developer Taskfile into namespaced, emoji-free tasks: `docker:*` for the local Compose stack, `podcastify:*` for feed generation and config scaffolding, `dev:*` for tests and validation. Keep `doctor`, `info`, `version`, and `health` at the root. End users who only run the published Docker image are unaffected.

## Modeling
- **Root** (`Taskfile.yml`): vars, dotenv, includes, `default`, `doctor`, `info`, `version`, `health`
- **docker** (`tasks/docker.yml`): lifecycle, logs, shell, build, compose, clean, env, fix:perms
- **podcastify** (`tasks/podcastify.yml`): generate, watch, new, clean:feeds, setup:dirs
- **dev** (`tasks/dev.yml`): test, test:coverage, test:ci, validate
- **Personal overrides**: optional `Taskfile.dev.yml` via include `devlocal` (does not clash with `dev:` namespace)

### Task mapping (old to new)

| Old | New |
|-----|-----|
| `up`, `down`, `restart`, `status` | `docker:up`, `docker:down`, `docker:restart`, `docker:status` |
| `logs`, `logs:recent`, `logs:errors` | `docker:logs`, `docker:logs:recent`, `docker:logs:errors` |
| `shell`, `shell:root`, `inspect` | `docker:shell`, `docker:shell:root`, `docker:inspect` |
| `build`, `build:quick`, `pull` | `docker:build`, `docker:build:quick`, `docker:pull` |
| `compose:config`, `compose:ps` | `docker:compose:config`, `docker:compose:ps` |
| `env` | `docker:env` |
| `clean:docker`, `clean:all` | `docker:clean`, `docker:clean:all` |
| `fix:perms` | `docker:fix:perms` |
| `generate`, `generate:watch`, `generate:watch-public` | `podcastify:generate`, `podcastify:watch`, `podcastify:watch-public` |
| `generate:silent` | `podcastify:generate:silent` (internal) |
| `new` | `podcastify:new` |
| `clean:feeds` | `podcastify:clean:feeds` |
| *(missing)* `setup:dirs` | `podcastify:setup:dirs` |
| `test`, `test:coverage`, `test:ci` | `dev:test`, `dev:test:coverage`, `dev:test:ci` |
| `doctor`, `info`, `version`, `health` | root (unchanged) |
| `docker:*` aliases, `gen` | removed |

## Constraints
- No emoji in Taskfile descriptions or command output.
- No backward-compat aliases for old root task names (`task up`, `task generate`, etc.).
- Task is for contributors only; do not require Task in end-user deployment docs.
- Do not change `docs/deployment.md` (no task references).
- Cross-namespace task calls use shell form (`task docker:build:quick`) where go-task namespace prefixing would break.

## Acceptance
- `task --list` shows `docker:*`, `podcastify:*`, and `dev:*` namespaces plus root tasks.
- No emoji in Taskfile(s).
- `podcastify:setup:dirs` exists; watch tasks depend on it.
- `podcastify:new` uses `.ai/templates/podcast-config-template.yaml`.
- `dev:validate` runs coverage tests and `docker:build:quick`.
- `task dev:test:coverage` passes with >= 90% coverage on `podcastify/`.
- `task docker:build:quick` succeeds.
- README, AGENTS.md, docs, `.ai/rules/rules.md`, and validate-changes skill use new task names.
- No stale `task up` / `task generate` / `task test:` references in project docs.

## Tasks
- [x] Split Taskfile into `Taskfile.yml` plus `tasks/docker.yml`, `tasks/podcastify.yml`, `tasks/dev.yml`
- [x] Remove emoji; fix internal task references and preconditions
- [x] Add `podcastify:setup:dirs`; wire watch dependencies
- [x] Add `dev:validate`; update validate-changes skill
- [x] Update README, AGENTS.md, docs/*, `.ai/rules/rules.md`
- [x] Run `task dev:test:coverage` and `task docker:build:quick` (via `task dev:validate`)

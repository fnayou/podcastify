# Podcastify — Rules

## AI & Agent Rules

- **`AGENTS.md`** is the source of truth regarding AI.
- **`.ai/`** is the directory where all AI files and resources belong (except `AGENTS.md`).
- The **`.ai/`** directory contains commands, rules, and skills that can be used, updated, and upgraded.
- **`.agents/rules/*.md`** files are optional tool-specific rules (not listed in `.ai/opencode.json` `instructions`); read and apply them when the task or tool requires it.

## Code Style

- Python: 4-space indent, UTF-8, LF line endings, trailing whitespace trimmed
- YAML: 2-space indent
- No comments unless explicitly requested
- `podcastify/` package with thin `app.py` entry point, class-based structure
- Follow existing naming conventions (PascalCase for classes, snake_case for functions)
- No unused imports or dead code

## Workflow Behavior

Each time we work on a feature on this project:

### 1. Discuss & Detail
Before creating a plan or writing code, we must thoroughly discuss the feature, clarify requirements, and detail the technical design. During this stage, the agent should actively ask the user any questions necessary to fully understand the feature and its implementation.

### 2. Plan Mode
Following discussion, we design and plan the feature. We can plan many features in advance and implement them later. The plan is saved as a markdown file inside the dedicated directory and must be sequentially enumerated: `.ai/plan/001-<slug>.md`, `.ai/plan/002-<slug>.md`, etc.

The plan file must follow this structure:

```markdown
# <Feature Name>

## Feature
<description of what the feature does>

## Modeling
<data models, schemas, relationships — if applicable>

## Constraints
<hard limits, invariants that must hold>

## Acceptance
<verifiable criteria that define done>

## Tasks
- [ ] Task 1 (description)
- [ ] Task 2 (description)
- [ ] ...
```

Plan files are local scratch files (gitignored).

### 3. Build Mode (Implementation)
When implementing from a plan file:
1. Read the plan from `.ai/plan/<slug>.md`.
2. Ask the user: "Proceed with the whole plan or step by step?"
   - **Step-by-step**: Execute one task at a time, confirm completion before moving to the next.
   - **Whole plan**: Execute all tasks sequentially.
3. **Task Tracking**: During implementation, each time the agent completes a task, the agent **must** immediately update the plan file to check it off (`- [x]`).
4. After all tasks are completed, **mandatory testing** must occur:
   a. Run ALL project tests (`task dev:test:coverage` or equivalent).
   b. Verify test coverage is at least 90%.
   c. Run local equivalents of GitHub Actions workflows (e.g., verifying `task docker:build` passes successfully to guarantee the Docker container remains stable).
   d. Verify all tests pass and satisfy all acceptance criteria.

### 4. Archive Plan
Once all tasks are completed, the implementation is verified, and the user gives explicit permission/approval, the plan file is archived by moving it to the `archive` subdirectory within the plan directory: `.ai/plan/archive/<slug>.md`.

## Project Constraints

- Docker-first workflow: build and run via `task docker:up`, generate via `task podcastify:generate`
- Config naming convention: `<name>-podcast.yaml` in `podcasts/`
- Media files live in `public/<name>/`, feeds are written to `public/<name>.xml`
- Episode GUIDs default to SHA-1 of `<podcast>/<filename>`
- No secrets or credentials in commits
- Core logic lives in the `podcastify/` package; `app.py` is a thin entry point
- The app runs inside a container; Caddy serves static files on `${PORT}`

## Testing

- **Mandatory End-of-Implementation Execution**: ALL tests must be fully executed at the very end of each feature implementation without fail.
- **GitHub Actions Parity**: Local testing should mimic the GitHub Actions CI workflow wherever possible. This includes running `task dev:test:ci` or `task dev:test:coverage` (for code tests) and verifying the Docker build (`task docker:build:quick` or `task dev:validate`) to ensure the container is stable.
- All new code must have corresponding tests.
- Tests use `pytest` + `pytest-mock` for mocking (ffprobe, filesystem).
- Tests live in `tests/`, one file per class, with fixtures in `tests/conftest.py`.
- Target: 90%+ coverage of `podcastify/`.

## Git Conventions

- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`
- No emojis in commit messages
- Never commit unless explicitly asked
- Never run `git push` or `git rebase` unless explicitly asked

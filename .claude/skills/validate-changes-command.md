# /validate-changes — Full Codebase Validation

## Trigger

User invokes `/validate-changes` or asks to run full local validation.

## Execution

1. Run the full validation task (preferred):

```bash
task dev:validate
```

This runs `dev:test:coverage` and `docker:build:quick`.

2. Or run steps individually:

```bash
task dev:test:coverage
task docker:build:quick
```

If `task` is unavailable, run:

```bash
python3 -m pytest tests/ --cov=podcastify --cov-report=term-missing --cov-fail-under=90 -v
docker compose build podcastify
```

3. Report results to the user in a concise summary:
   - Tests: pass/fail, coverage percentage
   - Docker build: pass/fail
   - Any errors with the relevant log excerpt

## Constraints

- Do not skip the coverage gate (90% minimum on `podcastify`).
- Run both tests and container build unless the user explicitly limits scope.
- Do not commit or push unless explicitly asked.

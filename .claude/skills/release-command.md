# /release — Changelog Generation

## Trigger

User invokes `/release` or asks to draft release notes from recent changes.

## Execution

1. Determine the version or range:
   - If the user provides a tag (e.g. `v1.2.0`), use it.
   - Otherwise inspect `git tag --sort=-v:refname` and recent commits.

2. Collect changes since the last release tag:

```bash
git log <last-tag>..HEAD --oneline
git diff <last-tag>..HEAD --stat
```

If no prior tag exists, use a reasonable commit range or ask the user.

3. Draft changelog sections:
   - **Added** — new features
   - **Changed** — behavior or API changes
   - **Fixed** — bug fixes
   - **Removed** — deprecations or removals
   - **Internal** — refactors, CI, docs (optional)

4. Present the changelog in markdown suitable for a GitHub Release body.

5. Do not create tags, commits, or push unless the user explicitly asks.

## Constraints

- Base entries on actual git history; do not fabricate changes.
- Use conventional commit prefixes from history when helpful (`feat:`, `fix:`, etc.).

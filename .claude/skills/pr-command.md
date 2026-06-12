# /pr — Pull Request Summary

## Trigger

User invokes `/pr` or asks to generate a PR summary from current git changes.

## Execution

1. Inspect repository state:
   - `git status`
   - `git diff` (unstaged)
   - `git diff --cached` (staged)
   - If on a feature branch: `git log main..HEAD --oneline` or `git log master..HEAD --oneline` (use whichever default branch exists)
   - `git diff main...HEAD` or `git diff master...HEAD` for full branch diff when useful

2. Draft a PR description using this structure:

```markdown
## Summary
- Bullet points of what changed and why

## Test plan
- [ ] Checklist of verification steps
```

3. Write the file to `.pr/pr-summary-YYYYMMDD-HHMM.md` using the current UTC or local date/hour (24h), e.g. `pr-summary-20250601-1430.md`.

4. Create `.pr/` if missing.

5. Tell the user the output path and a short summary of findings.

## Constraints

- Base content on actual `git` output; do not invent changes.
- Do not commit or push unless the user explicitly asks.
- `.pr/` is gitignored; never commit PR summaries.

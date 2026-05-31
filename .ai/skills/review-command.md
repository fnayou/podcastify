# /review — Pre-Commit Audit

## Trigger

User invokes `/review` or asks for a pre-commit code review.

## Execution

1. Read and apply project rules (already in OpenCode `instructions`: [AGENTS.md](../../AGENTS.md), [.ai/rules/rules.md](../rules/rules.md)).

2. Inspect changes:
   - `git status`
   - `git diff` and `git diff --cached`

3. Audit against project rules:
   - Python style (4-space, no unnecessary comments, no dead code)
   - Single-package architecture (`podcastify/`, thin `app.py` entry)
   - Config naming (`*-podcast.yaml`), media under `public/<name>/`
   - No secrets in diffs
   - New logic has tests; coverage target 90%+

4. Report findings grouped as:
   - **Blockers** — must fix before commit
   - **Suggestions** — optional improvements
   - **Looks good** — what passes review

5. If blockers exist, offer concrete fixes. Do not commit unless asked.

## Constraints

- Be specific: cite file paths and line-level issues when possible.
- Do not invent problems unrelated to the diff.

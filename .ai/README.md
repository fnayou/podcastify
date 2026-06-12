# .ai/

Tool-agnostic AI knowledge base. Not auto-loaded by Claude Code or OpenCode —
agents read these on demand when a task requires deeper context.

- `architecture/` — deep module/data-flow notes for AI agents (invariants,
  gotchas, file:line refs). Complements `docs/architecture.md` (human-facing),
  does not duplicate it.
- `decisions/` — ADRs, numbered `NNNN-slug.md`.
- `glossary.md` — domain term definitions.

Source of truth for the AI workflow remains `AGENTS.md` (root) and
`.claude/rules/rules.md`.

# Workflow Rules Update

## Feature
Establish a strict AI workflow pipeline (Discuss & Detail -> Plan Mode -> Build Mode -> Archive Plan) and formally define the system's source of truth (`AGENTS.md`) alongside agent-specific `.agents/rules/` directives.

## Modeling
N/A - Documentation and rulebook changes only.

## Constraints
- `AGENTS.md` must remain the absolute source of truth.
- `app.py` test coverage must be verified at >=90% upon completion of any Build Mode execution.
- Plans must be formally archived to `.opencode/plan/archive/` after completion.

## Acceptance
- `AGENTS.md` declares its role as the source of truth and references the `.opencode/plan/archive/` folder.
- `.opencode/rules/rules.md` comprehensively defines the 4-stage Workflow Behavior (Discuss, Plan, Build, Archive).
- The "Discuss & Detail" stage explicitly grants the agent permission to ask clarifying questions.
- `.opencode/opencode.json` automatically loads agent-specific rules like `.agents/rules/antigravity-rtk-rules.md`.

## Tasks
- [x] Task 1: Update `AGENTS.md` to clarify the role of the `.opencode/` directory and designate itself as the source of truth.
- [x] Task 2: Insert the AI & Agent Rules section into `.opencode/rules/rules.md`.
- [x] Task 3: Register `.agents/rules/antigravity-rtk-rules.md` within the `instructions` array of `.opencode/opencode.json`.
- [x] Task 4: Completely restructure the `Workflow Behavior` section of `.opencode/rules/rules.md` to introduce the explicit 4-stage pipeline (Discuss & Detail, Plan Mode, Build Mode, Archive Plan).
- [x] Task 5: Add a specific directive in `.opencode/rules/rules.md` authorizing the agent to ask questions during the 'Discuss & Detail' phase.
- [x] Task 6: Add the `.opencode/plan/archive/` directory to the `AGENTS.md` documentation tree.

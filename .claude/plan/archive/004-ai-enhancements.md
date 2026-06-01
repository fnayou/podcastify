# AI Tooling Enhancements

## Feature
Implement a suite of advanced AI capabilities to improve the agent workflow. This includes adding a `/review` command for pre-commit auditing, a `/release` command for changelog generation, a `.opencode/templates/` directory for boilerplate files, and updating the core agent configuration to utilize optimal Gemini models.

## Modeling
- **Commands**: `/review` and `/release` mapped in `.opencode/skills/`
- **Templates**: `.opencode/templates/podcast-config-template.yaml`, `.opencode/templates/test_template.py`
- **Agent Config**: `.opencode/opencode.json` modified to use Gemini models. Legacy model references were later removed due to OpenCode schema `additionalProperties: false` rejecting `_comment_*` fields.

## Constraints
- `.opencode/opencode.json` must remain valid JSON (OpenCode schema rejects unknown top-level keys via `additionalProperties: false`).
- Templates must precisely match the formats expected by the `app.py` parser.
- The `/review` skill must strictly enforce all rules defined in `.opencode/rules/rules.md`.

## Acceptance
- `opencode.json` sets `plan` to Gemini 3.1 Pro (Low), `build` to Gemini 3.5 Flash (Medium), and `reviewer` to Gemini 3.1 Pro (Low).
- Legacy models were initially preserved as `_comment` fields; these were later removed because OpenCode's strict schema rejects `additionalProperties`.
- `/review` and `/release` skill markdown files are successfully created in `.opencode/skills/`.
- Boilerplate templates exist in `.opencode/templates/`.

## Tasks
- [x] Task 1: Update `.opencode/opencode.json` to configure the `plan`, `build`, and `reviewer` agents with the new Gemini models. Legacy `_comment` fields were later removed due to schema validation (`additionalProperties: false`).
- [x] Task 2: Create the `.opencode/templates/` directory and populate it with a standard podcast YAML template and a pytest mock template.
- [x] Task 3: Create `.opencode/skills/review-command.md` to define the `/review` pre-commit audit behavior.
- [x] Task 4: Create `.opencode/skills/release-command.md` to define the `/release` changelog generation behavior.

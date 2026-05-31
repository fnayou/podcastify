# AI Tooling Enhancements

## Feature
Implement a suite of advanced AI capabilities to improve the agent workflow. This includes adding a `/review` command for pre-commit auditing, a `/release` command for changelog generation, a `.ai/templates/` directory for boilerplate files, and updating the core agent configuration to utilize optimal Gemini models.

## Modeling
- **Commands**: `/review` and `/release` mapped in `.ai/skills/`
- **Templates**: `.ai/templates/podcast-config-template.yaml`, `.ai/templates/test_template.py`
- **Agent Config**: `.ai/opencode.json` modified to use Gemini models, with legacy GLM/Kimi configs retained as JSON comments (`_comment`).

## Constraints
- `.ai/opencode.json` must remain valid JSON (using `_comment` fields instead of `//`).
- Templates must precisely match the formats expected by the `app.py` parser.
- The `/review` skill must strictly enforce all rules defined in `.ai/rules/rules.md`.

## Acceptance
- `opencode.json` sets `plan` to Gemini 3.1 Pro (Low), `build` to Gemini 3.5 Flash (Medium), and `reviewer` to Gemini 3.1 Pro (Low).
- Legacy models are preserved in the config as comments.
- `/review` and `/release` skill markdown files are successfully created in `.ai/skills/`.
- Boilerplate templates exist in `.ai/templates/`.

## Tasks
- [x] Task 1: Update `.ai/opencode.json` to configure the `plan`, `build`, and `reviewer` agents with the new Gemini models, preserving the old models in `_comment` fields.
- [x] Task 2: Create the `.ai/templates/` directory and populate it with a standard podcast YAML template and a pytest mock template.
- [x] Task 3: Create `.ai/skills/review-command.md` to define the `/review` pre-commit audit behavior.
- [x] Task 4: Create `.ai/skills/release-command.md` to define the `/release` changelog generation behavior.

# PR Command Skill

## Feature
Add an AI skill and command (`/pr`) that automatically generates a Pull Request summary based on the current git changes. The generated summary will follow a standard PR format and be saved as a uniquely timestamped markdown file inside an unversioned `.pr` directory.

## Modeling
- **Command Trigger**: `/pr`
- **Output Directory**: `.pr/`
- **Filename Format**: `pr-summary-YYYYMMDD-HHMM.md`
- **Skill Definition**: A new markdown file `.ai/skills/pr-command.md` describing the execution steps for the agent.

## Constraints
- The `.pr` directory must be ignored by git (added to `.gitignore`).
- The PR summary must be based directly on `git` diff outputs (staged, unstaged, or branch diffs).
- The filename must include the date and hour of creation to ensure uniqueness.

## Acceptance
- An LLM agent correctly identifies the `/pr` command.
- The agent runs git diff commands to inspect changes.
- The agent generates a comprehensive PR description.
- The agent writes the output to `.pr/pr-summary-YYYYMMDD-HHMM.md`.
- `.pr/` is successfully listed in `.gitignore`.

## Tasks
- [x] Task 1: Create the `.ai/skills/pr-command.md` file detailing the trigger and execution instructions for the agent.
- [x] Task 2: Ensure `.pr/` is appended to the `.gitignore` file.

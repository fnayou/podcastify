# Validate Changes Command Skill

## Feature
Add an AI skill and command (`/validate-changes`) that allows the user or agent to trigger a full validation of the codebase on demand. This ensures that all required code tests and container builds are successfully verified without manually typing out the individual commands.

## Modeling
- **Command Trigger**: `/validate-changes`
- **Skill Definition**: A new markdown file `.ai/skills/validate-changes-command.md` containing the execution steps for the agent.

## Constraints
- The command must execute the mandatory full testing suite (`task test:coverage` or `task test:ci`).
- The command must also verify the structural integrity of the project (e.g., executing a quick `task build` or equivalent to ensure the Docker configuration remains healthy).

## Acceptance
- An LLM agent correctly identifies the `/validate-changes` command.
- The agent automatically triggers all necessary local validations and GitHub Actions equivalents.
- The agent reports a summary of the test executions back to the user in a clean format.

## Tasks
- [x] Task 1: Create the `.ai/skills/validate-changes-command.md` file specifying the trigger and execution instructions (running both unit/coverage tests and container build checks).

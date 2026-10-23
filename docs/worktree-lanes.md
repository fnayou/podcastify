# Worktree lanes

A **lane** is a git worktree: another checkout of this repository in a sibling directory, on its own branch, opened as its own workspace in herdr and grouped under the repository. Lanes let several tickets move in parallel without stashing, switching branches under a running session, or letting two writers share one index.

Tools: [worktrunk](https://worktrunk.dev) (`wt`) creates worktrees and runs the project hooks, [herdr](https://herdr.dev) is the terminal, and the [herdr-worktrunk](https://github.com/devashish2203/herdr-worktrunk) plugin puts worktrunk behind a picker and opens each lane as a herdr workspace.

## What is shared between lanes

| Shared | Why | Protection |
|---|---|---|
| Host port | Two lanes publishing the same `HOST_PORT` collide. Compose project names come from the directory, so containers, networks and bind mounts are otherwise per lane. | One owner at a time, see the lane contract in [AGENTS.md](../AGENTS.md#worktree-lanes). |
| The remote and `main` | Every lane pushes to the same GitHub repository. | Merges only through a PR (rebase merge); worktrunk refuses local commits and merges. |

A lane is a concurrency boundary, not a credential sandbox: code in a lane can use everything the user's session can. Run a lane's branch code only when you trust it.

## Install

From the primary checkout:

```bash
task worktree:install
```

Safe to re-run. It installs `herdr`, `worktrunk`, `fzf` and `jq` with Homebrew if missing, installs the herdr-worktrunk plugin at one audited commit, writes the plugin config if there is none, records the approval of the project hooks in `.config/wt.toml`, then runs the checks. Check at any time, changing nothing:

```bash
task worktree:verify
```

It fails if a tool is missing, if worktrunk is not a measured version, if the plugin differs from the audited commit, if the hooks are not approved, or if the two refusal hooks do not refuse.

Two things the installer does not touch because they live in your dotfiles: herdr's `config.toml` and your shell rc. To open the picker from a key, add to herdr's config, then `herdr config check` and `herdr server reload-config`:

```toml
[[keys.command]]
key = "prefix+w"
type = "plugin_action"
command = "worktrunk.open"
description = "worktree: switch / create"
```

Without a binding: `herdr plugin action invoke open --plugin worktrunk`.

## Daily use

### Start a lane for a ticket

Open the picker and type the branch name, for example `feat/core-xml-escaping` (Conventional Commits types, see [contributing](contributing.md)). Worktrunk creates the lane from `main` in a sibling directory, runs the `pre-start` hook, and the plugin opens it as a herdr workspace under the repository. The hook copies the gitignored files listed in `.worktreeinclude` (`.env`).

From a terminal: `wt switch -c feat/<slug>`.

### Run the container in a lane

Give the lane its own port before starting anything, in the lane's `.env`:

```bash
HOST_PORT=8091
```

Pick a free port per lane. The lane that keeps the default 8080 is the resource owner: stop its containers (`task docker:down`) before another lane takes 8080.

### Merge

Never merge locally. Open a PR from the lane and rebase-merge it on GitHub. `wt merge` and `wt step commit` are refused by the hooks. Commit with git.

### Close a lane

1. The lane's work is merged and its tree is clean.
2. Stop containers started from the lane (`task docker:down`).
3. Close the herdr workspace, then remove the worktree and the local branch.

Removing a worktree or branch is destructive; do each step on purpose and check the result (`git worktree list`, `git branch`).

## Measuring a new worktrunk version

The merge refusal depends on the order in which worktrunk runs its hooks, so `tools/worktree-lanes.sh` accepts only versions listed in `WT_SUPPORTED`. To add a version, in a throwaway clone with `.config/wt.toml` copied in and committed with git on a side branch (the tree must be clean, or `--no-commit` refuses for the wrong reason), run each of these and require a refusal message, a non-zero exit, and an unchanged `main`:

```bash
wt hook pre-commit --yes
wt hook pre-merge --yes
wt merge main --yes
wt merge main --no-squash --no-commit --yes
```

If all four refuse, add the version to `WT_SUPPORTED`. Measured versions: 0.81.0.

## Plugin audit

The plugin is pinned to one commit because anyone can publish a herdr plugin without review. Bumping `PLUGIN_REF` in `tools/worktree-lanes.sh` is a re-audit of the plugin's scripts, not an edit.

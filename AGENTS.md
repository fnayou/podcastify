# Podcastify — AI Agent Instructions

## Project Overview

Podcastify is a tiny self-hosted podcast RSS generator. Drop MP3s into a folder, add a YAML config, and it builds iTunes-compatible RSS feeds. Served from a single Docker container (Caddy + Python).

- Repository: https://github.com/fnayou/podcastify
- Docker Hub: https://hub.docker.com/r/fnayou/podcastify
- License: MIT

## Tech Stack

- Python 3 (`podcastify/` package, thin `app.py` entry)
- PyYAML — config parsing
- Caddy — static file server (inside container)
- supervisord — process manager (inside container)
- Docker / Docker Compose — deployment
- Taskfile (go-task) — developer commands

## Directory Layout

```
app.py                  # CLI entry point
podcastify/             # Generator package (config, parser, media, rss, cli)
docker/podcastify/      # Dockerfile, Caddyfile, entrypoint, supervisord
podcasts/               # YAML configs: <name>-podcast.yaml
public/                 # Media + generated XML: <name>/ (media), <name>.xml (feed)
docs/                   # Human documentation (getting started, config, deployment, etc.)
Taskfile.yml            # Developer commands
docker-compose.yml      # Compose config
.editorconfig           # Indentation rules
.env.example            # Environment variable reference
```

## Commands

```bash
task docker:up                  # Build and start container
task docker:down                # Stop and remove
task podcastify:generate        # Run RSS generator
task docker:logs                # Follow logs
task podcastify:new NAME=myshow # Scaffold new podcast config
task doctor                     # Check environment
task podcastify:clean:feeds     # Remove generated XML
task dev:test:coverage          # Tests with coverage gate
```

## Architecture (podcastify/)

| Class / Module      | Responsibility                              |
|---------------------|---------------------------------------------|
| Config              | Environment variables and field constants    |
| MediaProcessor      | ffprobe duration extraction, persistent cache|
| ConfigurationManager| YAML loading, metadata extraction, discovery |
| EpisodeManager      | Episode discovery, image URL resolution      |
| RSSGenerator        | iTunes-compatible XML feed generation        |
| PodcastProcessor    | Orchestration: load → validate → generate   |

## AI Workflow

- **`AGENTS.md`** is the source of truth regarding AI.
- **`.ai/`** is the directory where all AI files and resources belong (except `AGENTS.md`).
- The **`.ai/`** directory contains commands, rules, skills, and OpenCode configuration.

Detailed rules live in [`.ai/rules/rules.md`](.ai/rules/rules.md).

### Directory layout (`.ai/`)

```
.ai/
  opencode.json       # OpenCode agent and skill configuration
  rules/rules.md      # Project rules (auto-loaded)
  skills/             # Workflow definitions (how to perform each task)
  commands/           # Slash commands that delegate to a skill
  plan/               # Feature plans (gitignored scratch)
    archive/          # Completed plans
  templates/          # Boilerplate (podcast YAML, test template)
.opencode/
  commands/           # Symlink to .ai/commands/ (OpenCode TUI discovery)
.agents/rules/        # Optional tool-specific rules (read when relevant)
```

### OpenCode ([`.ai/opencode.json`](.ai/opencode.json))

Set `OPENCODE_CONFIG=.ai/opencode.json` in `.env` (see [`.env.example`](.env.example)).

| Setting | Value |
|---------|--------|
| `default_agent` | `plan` |
| **Instructions** (always loaded) | `.ai/rules/rules.md`, `AGENTS.md` |
| **Skills** | `.ai/skills/` |

| Agent | Model | Used by |
|-------|--------|---------|
| `plan` | `opencode-go/glm-5.1` | Planning, `/release` |
| `build` | `opencode-go/kimi-k2.6` | Implementation, `/pr`, `/validate-changes` |
| `reviewer` | `opencode-go/kimi-k2.6` | `/review` |

Legacy Gemini model IDs are kept in `_comment_legacy_*` fields in the config file for reference only.

### Slash commands

Commands live in [`.ai/commands/`](.ai/commands/). Each file runs its matching skill under [`.ai/skills/`](.ai/skills/):

| Command | Skill | Agent |
|---------|-------|--------|
| `/pr` | `pr-command.md` | `build` |
| `/review` | `review-command.md` | `reviewer` |
| `/release` | `release-command.md` | `plan` |
| `/validate-changes` | `validate-changes-command.md` | `build` |

### Optional agent rules

[`.agents/rules/`](.agents/rules/) (e.g. `antigravity-rtk-rules.md`) is **not** auto-loaded by OpenCode. Follow those files when the workflow or tool requires them (shell/RTK usage, specific IDE agents).

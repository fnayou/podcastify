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
- **`.claude/`** is the directory where all AI files and resources belong (except `AGENTS.md`).
- The **`.claude/`** directory contains agents, commands, rules, skills, plans, and templates.
- **`.opencode/`** contains only `opencode.json` — OpenCode tool configuration, pointing into `.claude/`.

Detailed rules live in [`.claude/rules/rules.md`](.claude/rules/rules.md).

### Directory layout (`.claude/`)

```
.claude/
  agents/             # Claude Code subagent definitions
  rules/rules.md      # Project rules (auto-loaded by OpenCode)
  skills/             # Workflow definitions (how to perform each task)
  commands/           # Slash commands that delegate to a skill
  plan/               # Feature plans (gitignored scratch)
    archive/          # Completed plans
  templates/          # Boilerplate (podcast YAML, test template)
```

### OpenCode ([`.opencode/opencode.json`](.opencode/opencode.json))

Set `OPENCODE_CONFIG=.opencode/opencode.json` in `.env` (see [`.env.example`](.env.example)).

| Setting | Value |
|---------|--------|
| `default_agent` | `planner` |
| **Instructions** (always loaded) | `.claude/rules/rules.md`, `AGENTS.md` |
| **Skills** (flat command-templates) | `.claude/skills/*-command.md` |

| Agent | Mode | OpenCode model | Claude Code model | Used by |
|-------|------|---|---|---|
| `planner` | primary | `opencode-go/glm-5.1` | Sonnet 4.6 | Planning, design, `/release` |
| `builder` | primary | `opencode-go/kimi-k2.6` | Haiku 4.5 | Implementation, `/pr`, `/validate-changes` |
| `reviewer` | subagent | `opencode-go/kimi-k2.6` | Sonnet 4.6 | Code audit, `/review` |
| `architect` | subagent | `opencode-go/glm-5.1` | Opus 4.8 | Complex design, documentation |

**Note**: Model IDs differ between OpenCode (opencode-go/*) and Claude Code (Sonnet/Haiku/Opus) — different providers, same roles. Alignment is on names/modes/permissions, not LLM choice.

### Slash commands

Commands defined inline in [`.opencode/opencode.json`](.opencode/opencode.json), referencing flat skill templates under [`.claude/skills/`](.claude/skills/):

| Command | Agent | Skill template |
|---------|-------|---|
| `/pr` | builder | `@.claude/skills/pr-command.md` |
| `/review` | reviewer | `@.claude/skills/review-command.md` |
| `/release` | planner | `@.claude/skills/release-command.md` |
| `/validate-changes` | builder | `@.claude/skills/validate-changes-command.md` |

### Optional agent rules

External tool-specific rules files are **not** auto-loaded by OpenCode or Claude Code. Follow them when the workflow or tool requires them (shell/RTK usage, specific IDE agents).

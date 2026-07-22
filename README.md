# AdaL Skills Marketplace

Essential skills for teams and developers building software with best engineering practices and 10x productivity. Compatible with [AdaL CLI](https://sylph.ai) and Claude Code.

## Installation

> **Both AdaL CLI and Claude Code use the same commands.**

### Step 1: Add the Marketplace

```
/plugin marketplace add SylphAI-Inc/skills
```

### Step 2: Browse and Install

Use the `/plugin` command to browse available plugins and install:

```
/plugin
```

Then follow the interactive dialog:
1. Select **Browse and install plugins**
2. Select **adal-agent-skills** marketplace
3. Select **core-skills** plugin
4. Select **Install now**

Or install directly:

```
/plugin install core-skills@adal-agent-skills
```

> **Format:** `/plugin install <plugin-name>@<marketplace-name>`

### Step 3: View Available Skills

After installation, see all your available skills:

```
/skills
```

## Available Skills

### Core Skills (`core-skills` plugin)

| Skill | Description |
|-------|-------------|
| [create-skill](./skills/create-skill/SKILL.md) | Guide for creating AdaL skills - personal, project, or plugin |
| [posthog-analytics](./skills/posthog-analytics/SKILL.md) | Automate PostHog dashboard creation, sync, and export via API |
| [clone-anywebsite](./skills/clone-anywebsite/SKILL.md) | Clone any website's landing page with pixel-perfect fidelity — visual-first workflow with sniper CSS extraction, animation detection, and mandatory Builder+Evaluator pattern |
| [glowmotion](./skills/glowmotion/SKILL.md) | Create premium animated technical diagrams (flowcharts, architecture diagrams, Mermaid conversions) as single self-contained HTML+SVG files with glowing comet-dot flows, pulsing highlights, and a built-in light/dark theme toggle |

### SWE CLI Skills (`swe-cli-skills` plugin)

> **man pages for machines** 🤖 — Your agent knows the commands. We teach it the workflows.

23 expert CLI guides across 9 categories. Senior engineer judgment — not reference docs, but operational workflows, safety guardrails, gotchas, error recovery, and anti-patterns.

| Category | CLIs |
|----------|------|
| ☁️ Cloud | AWS, gcloud, Azure |
| 🏗️ IaC | Terraform |
| 🐳 Containers | Docker, kubectl, Helm |
| 🔀 Git & VCS | Git, GitHub CLI |
| 🛠️ Dev Tools | jq, sed, make |
| 🌐 Networking | curl, SSH/SCP |
| 📦 Package Managers | npm, pip/uv |
| 🗄️ Databases | psql, redis-cli |
| 🚀 Platforms | Stripe, Sentry, Vercel, Firebase, Fly.io |

Install: `/plugin install swe-cli-skills@adal-agent-skills`

See the full [swe-cli-skills README](./skills/swe-cli-skills/README.md) for details.

## Creating Your Own Skills

See the [create-skill](./skills/create-skill/SKILL.md) guide for instructions on:
- **Personal skills** (`~/.adal/skills/`) - Private to you
- **Project skills** (`.adal/skills/`) - Shared via git with your team
- **Plugin skills** (GitHub repo) - Public, shareable via marketplace
## Repository Structure

```text
.
├── .claude-plugin/
│   └── marketplace.json       # Plugin metadata and skill registry (required path)
├── README.md                  # This file
└── skills/                    # All skills organized by name
    ├── clone-anywebsite/
    │   └── SKILL.md
    ├── create-skill/
    │   └── SKILL.md
    ├── glowmotion/             # Animated HTML+SVG diagram generator
    │   ├── SKILL.md
    │   ├── references/
    │   └── scripts/
    ├── posthog-analytics/
    │   └── SKILL.md
    └── swe-cli-skills/        # 23 CLI guides for AI coding agents
        ├── SKILL.md            # Entry point (index + quick reference)
        └── skills/
            ├── cloud/          # AWS, gcloud, Azure
            ├── iac/            # Terraform
            ├── containers/     # Docker, kubectl, Helm
            ├── git-vcs/        # Git, GitHub CLI
            ├── dev-tools/      # jq, sed, make
            ├── networking/     # curl, SSH
            ├── package-managers/ # npm, pip/uv
            ├── databases/      # psql, redis-cli
            └── platforms/      # Stripe, Sentry, Vercel, Firebase, Fly.io
```

## Contributing

1. Fork this repository
2. Create a new skill in `skills/<skill-name>/SKILL.md`
3. Add the skill to `marketplace.json` under the appropriate plugin
4. Submit a pull request

### SKILL.md Format

```markdown
---
name: skill-name
description: Brief description for the skills list
author: your-username
version: 1.0.0
---

# Skill Title

## When to Use
Describe trigger conditions

## Instructions
Step-by-step guidance for the agent
```

## License

MIT License - see [LICENSE](./LICENSE) for details.

# AdaL Skills

Essential skills for teams and developers building software with best engineering practices. One `SKILL.md` folder per skill — usable by [AdaL CLI](https://sylph.ai), Claude Code, and any agent that speaks the [`@skills:` protocol](https://github.com/SylphAI-Inc/atskills).

**It's just a file tree.** No manifest to maintain, no `marketplace.json` to register with, no bundle or plugin concepts to learn. A folder holding a `SKILL.md` is a skill; its path is its address; the tree is the marketplace.

## Use a skill — nothing to install

Every path in this repo is an address. Reference it and it loads, right now:

```
@skills:gh:sylphai-inc/skills/skills/posthog-analytics   set up our dashboards
```

That's the whole integration. Reading is using; nothing is installed, nothing stays resident.

**And `@` comes with the user experience you already have.** Typing `@` autocompletes skills in the same dropdown you already use for files and directories: the project's own skills and every followed cloud ID complete instantly, each suggestion showing where it lives. A skill you've used is one keystroke away; a skill you've never seen is one pasted path away (GitHub URLs work as-is). The flexibility of addressing anything by path, with the muscle memory of `@`-mentioning a file — no new gesture to learn.

## Highlight 1 — skills managed like a filesystem

**A path addresses any granularity: one skill, a collection, or the whole tree.** `@skills:` references, saves, and auto-trigger lines all respect the same GitHub path relations:

```
@skills:gh:sylphai-inc/skills                          the whole repo -> a menu
@skills:gh:sylphai-inc/skills/skills                   the collection -> a menu
@skills:gh:sylphai-inc/skills/skills/create-skill      one skill -> its body
@skills:gh:sylphai-inc/skills/skills/create-skill:save vendor it, adapt it, own it
```

A directory is a **menu** — one line per skill, every line itself a valid address — so browsing and using are the same gesture. Take the tree piece by piece: load one subtree now, a sibling later, and the validating cache means nothing is ever downloaded twice — each use asks "did this change?" and unchanged content serves instantly. Saves vendor at the ID's own path (`.atskills/gh/sylphai-inc/skills/...`), so copies from one source nest together and every saved copy answers its own address, exactly like Go's `vendor/` directory.

Manage skills the way you manage files: by path, at whatever granularity the moment needs. There is no bundle format because none is needed — a "bundle" is just a directory, and you take skills from it one path at a time.

## Highlight 2 — one config file, `.gitignore` semantics

**Everything that fires on its own is one readable file**: `.atskills/.autotrigger`, one line per entry, exactly like `.gitignore` — and with the same flexibility about which parts are on:

```
# .atskills/.autotrigger
sec-checklist                              your skill — auto-triggers
team-flows/                                every skill under the directory
!team-flows/experimental                   ...except that one
@gh:sylphai-inc/skills/skills/create-skill follow this repo's latest
@gh:sylphai-inc/skills/skills/             follow the whole collection
```

Install = add a line. Uninstall = remove it. A directory line covers present *and future* skills under it; a `!` negation carves out exceptions; an `@` line follows upstream so the provider keeps it current. One `git diff` line per decision, reviewed like any other change — no manifest, no lockfile, no per-machine state.

## Highlight 3 — `/skills`: one surface manages it all

You never have to touch a dotfile. `/skills` is a checkbox tree over `.autotrigger` and `.atskills/` — every kind of line (your local skills, `gh:` GitHub follows, hub follows) and every kind of storage (your own folders, saved copies with their `.source` provenance) in one view:

```
/skills
  [~] team-flows/              a directory line, partially on
      [x] deploy
      [ ] review
  [x] my-tdd                   yours
  [x] @gh:sylphai-inc/skills/skills/create-skill   cloud · auto-updates
```

Check a box → a line is written. Uncheck under a covering directory → the line **splits** so the file always reads true. `a` adds any skill by ID (pasted GitHub URLs work), `x` removes a saved folder and its line, and *view prompt* shows the exact text the model sees, word for word, with its token count. Every checkbox action is equally a typed command (`/skills install|uninstall|toggle|save|remove <path>`) and equally a hand edit — three ways to write the same one-line diffs.

## Try it

```
@skills:gh:sylphai-inc/skills/skills      # browse this repo's collection
/skills                                   # manage: checkbox tree over .autotrigger
/skills install gh:sylphai-inc/skills/skills/posthog-analytics
```

## Available Skills

| Skill | Description |
|-------|-------------|
| [create-skill](./skills/create-skill/SKILL.md) | Guide for creating AdaL skills - personal, project, or plugin |
| [posthog-analytics](./skills/posthog-analytics/SKILL.md) | Automate PostHog dashboard creation, sync, and export via API |
| [clone-anywebsite](./skills/clone-anywebsite/SKILL.md) | Clone any website's landing page with pixel-perfect fidelity — visual-first workflow with sniper CSS extraction, animation detection, and mandatory Builder+Evaluator pattern |
| [glowmotion](./skills/glowmotion/SKILL.md) | Create premium animated technical diagrams (flowcharts, architecture diagrams, Mermaid conversions) as single self-contained HTML+SVG files with glowing comet-dot flows, pulsing highlights, and a built-in light/dark theme toggle |
| [codegraph](./skills/codegraph/SKILL.md) | Turn any codebase into an explorable interactive graph — deterministic structural scan (imports, symbols, PageRank importance, architectural layers, dependency cycles, entry points) plus AI summaries and guided tours, delivered as one self-contained HTML file |

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

## Classic plugin install (compatible)

The marketplace/plugin path keeps working unchanged, in both AdaL CLI and Claude Code:

```
/plugin marketplace add SylphAI-Inc/skills
/plugin install core-skills@adal-agent-skills
/skills
```

## Creating Your Own Skills

See the [create-skill](./skills/create-skill/SKILL.md) guide for instructions on:
- **Personal skills** (`~/.adal/skills/`) - Private to you
- **Project skills** (`.atskills/` or `.adal/skills/`) - Shared via git with your team
- **Public skills** (GitHub repo) - Shareable by path, no packaging required

## Repository Structure

```text
.
├── .claude-plugin/
│   └── marketplace.json       # Plugin metadata (classic install path only)
├── README.md                  # This file
└── skills/                    # All skills organized by name — every folder an address
    ├── clone-anywebsite/
    │   └── SKILL.md
    ├── codegraph/              # Interactive codebase graph generator
    │   ├── SKILL.md
    │   └── scripts/
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
3. (Classic path only) add it to `marketplace.json`
4. Submit a pull request — merged skills are instantly addressable as `gh:sylphai-inc/skills/skills/<name>`

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

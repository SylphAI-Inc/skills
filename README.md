# AdaL Skills Marketplace

Official collection of community-shareable skills for [AdaL CLI](https://sylph.ai).

## Installation

Add this skills repository to your AdaL installation:

```bash
/plugin marketplace add SylphAI-Inc/skills
```

Or add specific plugins:

```bash
/plugin marketplace add SylphAI-Inc/skills@core-skills
```

## Available Skills

### Core Skills (`core-skills` plugin)

| Skill | Description |
|-------|-------------|
| [create-skill](./skills/create-skill/SKILL.md) | Guide for creating AdaL skills - personal, project, or plugin |

## Creating Your Own Skills

See the [create-skill](./skills/create-skill/SKILL.md) guide for instructions on:
- **Personal skills** (`~/.adal/skills/`) - Private to you
- **Project skills** (`.adal/skills/`) - Shared via git with your team
- **Plugin skills** (GitHub repo) - Public, shareable via marketplace

## Repository Structure

```
skills/
├── marketplace.json       # Plugin metadata and skill registry
├── README.md              # This file
└── skills/                # All skills organized by name
    └── <skill-name>/
        └── SKILL.md       # Skill instructions (required)
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

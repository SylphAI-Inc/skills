# Skill Template

Use this template to create a new CLI guide. Copy it to `skills/your-cli.md` and fill in each section.

---

```yaml
---
name: cli-name
description: "One-line description of what this guide covers"
version: "CLI version this guide targets (e.g., 2.x, 1.28+)"
category: cloud | iac | containers | git-vcs | dev-tools | networking | databases | ci-cd | package-managers | monitoring | languages-runtimes
---
```

# CLI Name

> **Official docs:** https://docs.example.com/ | **Reference:** https://docs.example.com/reference/

One-sentence description of the CLI and its primary use case.

## Setup & Auth

How to install, configure, and verify the CLI is working.
Include auth methods (API keys, SSO, env vars, config files).

```bash
# Installation
# ...

# Auth configuration
# ...

# Verify setup
# ...
```

## Core Workflows

The 20% of commands that cover 80% of daily usage.
Organize by task, not alphabetically.

### Workflow: [Task Name]

```bash
# Step 1: ...
# Step 2: ...
# Step 3: ...
```

## Flag Gotchas

Flags that behave unexpectedly, ordering traps, and version-specific quirks.

### [Gotcha Title]

```bash
# ❌ WRONG — explanation of why
command --flag-a --flag-b

# ✅ CORRECT — explanation of fix
command --flag-b --flag-a
```

## Error Patterns

Common errors and their actual fixes (not generic advice).

### `Error message text`

**Cause:** Why this happens.

**Fix:**
```bash
# specific fix command
```

## Anti-Patterns

Things that look correct but cause problems. "Never do X because Y."

### [Anti-Pattern Title]

```bash
# ❌ NEVER do this — because [reason]
dangerous-command

# ✅ Instead, do this
safe-alternative
```

## Composability

How this CLI pipes into and works with other CLIs.

```bash
# Example: cli-name + jq
cli-name output-command | jq '.field'

# Example: cli-name + xargs
cli-name list-command | xargs -I {} cli-name action {}
```

## Agent Constraints

Special considerations for AI agents (no TTY, no interactive prompts, automation contexts).

```bash
# ❌ HANGS in agent context — requires interactive input
interactive-command

# ✅ Non-interactive alternative
non-interactive-command --flag
```

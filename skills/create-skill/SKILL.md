---
name: create-skill
description: Guide users through creating AdaL skills by clarifying the skill type (personal, project, or public plugin) and scaffolding the appropriate structure.
author: SylphAI-Inc
version: 1.0.0
---

# Create Skill

Use this skill when the user asks to create a skill, make a skill, add a new skill, or similar requests.

## When to Use

Trigger when user mentions:
- "create a skill"
- "make a skill"
- "add a new skill"
- "write a skill"
- "scaffold a skill"
- "set up a skill"

## Step 1: Clarify Skill Type

**Always ask the user which type of skill they want to create:**

| Type | Location | Visibility | Use Case |
|------|----------|------------|----------|
| **Personal** | `~/.adal/skills/<name>/` | Only you | Custom workflows, personal preferences |
| **Project** | `.adal/skills/<name>/` | Team (via git) | Team conventions, project-specific patterns |
| **Plugin** | GitHub repo | Public | Community-shareable, reusable across projects |

**Example prompt:**
> What type of skill would you like to create?
>
> 1. **Personal skill** (`~/.adal/skills/`) - Just for you, not shared
> 2. **Project skill** (`.adal/skills/`) - Shared with your team via git
> 3. **Plugin skill** (GitHub repo) - Public, shareable with the community
>
> Which type? (1/2/3)

## Step 2: Gather Skill Details

Ask for:
1. **Skill name** - lowercase, hyphenated (e.g., `my-workflow`, `team-conventions`)
2. **Description** - Brief explanation of what it does and when to use it
3. **When to trigger** - Keywords or scenarios that should activate this skill

## Step 3: Create the Skill Structure

### For Personal Skills (`~/.adal/skills/`)

```bash
mkdir -p ~/.adal/skills/<skill-name>
```

Create `SKILL.md`:
```markdown
---
name: <skill-name>
description: <Brief description>
---

# <Skill Title>

## When to Use
<Describe trigger scenarios>

## Instructions
<Step-by-step guidance for the agent>
```

### For Project Skills (`.adal/skills/`)

```bash
mkdir -p .adal/skills/<skill-name>
```

Same `SKILL.md` format. Remember to commit to git for team sharing.

### For Plugin Skills (GitHub)

1. Create a GitHub repository with structure:
   ```
   <repo>/
   ├── marketplace.json     # Metadata for the marketplace
   └── skills/
       └── <skill-name>/
           └── SKILL.md
   ```

2. `marketplace.json` format:
   ```json
   {
     "name": "my-skills",
     "description": "My collection of skills",
     "version": "1.0.0",
     "author": "your-username",
     "plugins": [
       {
         "name": "my-plugin",
         "description": "Plugin description",
         "skills": ["skill-name"]
       }
     ]
   }
   ```

3. Users can install with: `/plugin marketplace add <owner>/<repo>`

## Step 4: Verify Installation

After creating:
- Run `/skills` to verify the skill appears
- Test by asking the agent to perform a task the skill should handle

## Advanced Options

If the user wants multi-file skills, guide them on:
- **REFERENCE.md** - Detailed documentation
- **scripts/** - Executable utilities (Python, bash)
- Link supporting files from SKILL.md

## Example Interaction

**User:** "Create a skill for our API conventions"

**Agent:** "What type of skill would you like?
1. Personal - just for you
2. Project - shared with team via git
3. Plugin - public on GitHub"

**User:** "Project"

**Agent:** "I'll create `.adal/skills/api-conventions/`. What conventions should it include?"

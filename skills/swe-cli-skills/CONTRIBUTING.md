# Contributing to swe-cli-skills

Thank you for contributing CLI expertise! Every skill you add helps thousands of AI agents operate more safely and effectively.

## How to Contribute

### Adding a New CLI Guide

1. **Check if it exists** — Look in the skills table in [README.md](README.md) and [SKILL.md](SKILL.md)
2. **Copy the template** — `cp SKILL_TEMPLATE.md skills/your-cli.md`
3. **Fill in all 7 sections** — See guidelines below
4. **Add official doc links** — Include a `> **Official docs:**` line after the title
5. **Update SKILL.md** — Add your CLI to the table in `SKILL.md`
6. **Update README.md** — Add your CLI to the skills table
7. **Open a PR** — One CLI per PR preferred

### Writing Guidelines

#### What Makes a Great Guide

- **Opinionated workflows** — Not "here are all the flags" but "here's how a senior engineer does this"
- **Real gotchas** — Things you've personally been burned by
- **Concrete error patterns** — Actual error messages with actual fixes
- **Agent-aware** — Always include non-interactive alternatives
- **Composable** — Show how the CLI works with others (pipes, scripts)

#### What to Avoid

- ❌ Copying the official docs / man page
- ❌ Listing every flag and option
- ❌ Generic advice ("be careful with this command")
- ❌ Untested commands
- ❌ Platform-specific instructions without labeling (mark macOS/Linux/Windows)

#### Required Format

Every guide must include:
1. YAML frontmatter with `name`, `description`, `version`, `category`
2. Official docs link: `> **Official docs:** <url>`
3. All 7 sections: Setup & Auth, Core Workflows, Flag Gotchas, Error Patterns, Anti-Patterns, Composability, Agent Constraints
4. `# ❌ WRONG` and `# ✅ CORRECT` markers for wrong/right patterns
5. Explanations of *why* something is wrong, not just *what* to do instead

#### Tone

- Write as if you're teaching a smart junior engineer
- Keep code blocks focused — one concept per block
- Always explain *why* something is wrong, not just what to do instead

### Improving an Existing Guide

Found a mistake or know a better pattern? PRs welcome:

1. Describe the issue in the PR body
2. Show the before/after
3. Explain why the new version is better

### Quality Checklist

Before submitting, verify:

- [ ] YAML frontmatter has `name`, `description`, `version`, `category`
- [ ] Official docs link is included after the title
- [ ] All 7 sections are present
- [ ] Code examples are tested and correct
- [ ] ❌/✅ markers are used for wrong/right patterns
- [ ] CLI version is specified in frontmatter
- [ ] `SKILL.md` table is updated
- [ ] `README.md` skills table is updated

## Code of Conduct

Be respectful, be helpful, be accurate. We're building a knowledge base that agents will trust — accuracy matters more than quantity.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

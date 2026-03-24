# swe-cli-skills

### man pages for machines 🤖

> Your agent knows the commands. We teach it the workflows.

**swe-cli-skills** is an open-source skill that gives AI coding agents senior-engineer-level CLI expertise. It covers **23 CLIs** across 9 categories — not just flag syntax, but operational workflows, safety guardrails, gotchas, error recovery, and composition patterns.

**One skill. Twenty-three CLIs. Every coding agent.**

---

## ⚡ Install in 30 Seconds

### npx ([skills CLI](https://skills.sh/docs/cli))

```bash
npx skills add SylphAI-Inc/swe-cli-skills
```

Downloads and configures the skill for your AI agent. Works with [AdaL](https://docs.sylph.ai/), Claude Code, Codex, Gemini CLI, GitHub Copilot, Cursor, Windsurf, and more.

### AdaL Plugin Marketplace

```bash
# Add the marketplace (one-time)
/plugin marketplace add SylphAI-Inc/swe-cli-skills

# Install the skill
/plugin install swe-cli-skills@swe-cli-skills
```

### Manual Install (per agent)

<details>
<summary>AdaL</summary>

```bash
# Project-level (recommended)
git clone https://github.com/SylphAI-Inc/swe-cli-skills.git .adal/skills/swe-cli-skills

# Personal (available in all projects)
git clone https://github.com/SylphAI-Inc/swe-cli-skills.git ~/.adal/skills/swe-cli-skills
```
</details>

<details>
<summary>Claude Code</summary>

```bash
cd your-project
git clone https://github.com/SylphAI-Inc/swe-cli-skills.git .claude/skills/swe-cli-skills
```
</details>

<details>
<summary>Codex / OpenAI Agents</summary>

```bash
git clone https://github.com/SylphAI-Inc/swe-cli-skills.git .codex/skills/swe-cli-skills
```
</details>

<details>
<summary>Gemini CLI</summary>

```bash
git clone https://github.com/SylphAI-Inc/swe-cli-skills.git .gemini/skills/swe-cli-skills
```
</details>

<details>
<summary>GitHub Copilot</summary>

```bash
git clone https://github.com/SylphAI-Inc/swe-cli-skills.git .github/skills/swe-cli-skills
```
</details>

<details>
<summary>Cursor / Windsurf / Any SKILL.md Agent</summary>

```bash
git clone https://github.com/SylphAI-Inc/swe-cli-skills.git <agent-skills-dir>/swe-cli-skills
```
</details>

---

## 🎯 Why This Exists

AI coding agents generate CLI commands that *look* right but fail in production:

```bash
# Your agent generates this (WRONG):
aws s3 sync . s3://bucket --include "*.json" --exclude "*"
# Syncs NOTHING — filters are applied left-to-right

# With swe-cli-skills loaded, it generates this (CORRECT):
aws s3 sync . s3://bucket --exclude "*" --include "*.json"
```

```bash
# Your agent runs this (DANGEROUS):
terraform import aws_s3_bucket.logs my-app-logs
# No state backup, no lock, no plan after — drift goes undetected

# With swe-cli-skills loaded:
terraform state pull > backup-$(date +%Y%m%d).tfstate
terraform import -lock=true aws_s3_bucket.logs my-app-logs
terraform plan  # Always verify after import
```

```bash
# Your agent tries this (HANGS):
git rebase -i HEAD~3
# No TTY available — agent is stuck forever

# With swe-cli-skills loaded:
GIT_SEQUENCE_EDITOR="sed -i 's/pick/squash/2'" git rebase -i HEAD~3
```

**The pattern:** Models know CLI syntax. They don't know CLI *wisdom*.

---

## 📚 What's Included

One `SKILL.md` entry point → 9 categories → 23 expert CLI guides:

### ☁️ Cloud

| CLI | Guide | What You Get |
|-----|-------|-------------|
| **AWS CLI** | [`skills/cloud/aws.md`](skills/cloud/aws.md) | S3 filter ordering, JMESPath queries, IAM auth, Lambda workflows |
| **gcloud** | [`skills/cloud/gcloud.md`](skills/cloud/gcloud.md) | GCP project/config, GKE, Cloud Run, IAM, logging & monitoring |
| **Azure CLI** | [`skills/cloud/azure.md`](skills/cloud/azure.md) | Resource groups, AKS, App Service, RBAC, ARM deployments |

### 🏗️ Infrastructure as Code

| CLI | Guide | What You Get |
|-----|-------|-------------|
| **Terraform** | [`skills/iac/terraform.md`](skills/iac/terraform.md) | Safe import, state management, plan-before-apply, workspace migration |

### 🐳 Containers & Orchestration

| CLI | Guide | What You Get |
|-----|-------|-------------|
| **Docker** | [`skills/containers/docker.md`](skills/containers/docker.md) | Build cache optimization, compose v2, cleanup, multi-arch builds |
| **kubectl** | [`skills/containers/kubectl.md`](skills/containers/kubectl.md) | Context safety, namespace gotchas, rollout/rollback, pod debugging |
| **Helm** | [`skills/containers/helm.md`](skills/containers/helm.md) | Values precedence, upgrade resets, release state, chart debugging |

### 🔀 Git & Version Control

| CLI | Guide | What You Get |
|-----|-------|-------------|
| **Git** | [`skills/git-vcs/git.md`](skills/git-vcs/git.md) | Non-interactive rebase/merge, conflict resolution, TTY workarounds |
| **GitHub CLI** | [`skills/git-vcs/gh.md`](skills/git-vcs/gh.md) | PR workflows, issue management, releases, Actions inspection |

### 🛠️ Dev Tools

| CLI | Guide | What You Get |
|-----|-------|-------------|
| **jq** | [`skills/dev-tools/jq.md`](skills/dev-tools/jq.md) | select vs map, array ops, shell variable injection, composition |
| **curl** | [`skills/dev-tools/curl.md`](skills/dev-tools/curl.md) | Auth headers, multipart uploads, response debugging, API patterns |
| **SSH/SCP** | [`skills/dev-tools/ssh.md`](skills/dev-tools/ssh.md) | Tunnel direction, ProxyJump, key management, BatchMode for agents |
| **sed** | [`skills/dev-tools/sed.md`](skills/dev-tools/sed.md) | Stream editing, in-place substitution, macOS vs Linux portability |
| **make** | [`skills/dev-tools/make.md`](skills/dev-tools/make.md) | Build automation, Makefile patterns, phony targets, tab-vs-spaces |

### 📦 Package Managers

| CLI | Guide | What You Get |
|-----|-------|-------------|
| **npm** | [`skills/package-managers/npm.md`](skills/package-managers/npm.md) | Dependency management, scripts, workspaces, publishing, lockfiles |
| **pip & uv** | [`skills/package-managers/pip-uv.md`](skills/package-managers/pip-uv.md) | Virtual envs, dependency resolution, uv acceleration, constraints |

### 🗄️ Databases

| CLI | Guide | What You Get |
|-----|-------|-------------|
| **psql** | [`skills/databases/psql.md`](skills/databases/psql.md) | Connection strings, non-interactive queries, backup/restore, meta-commands |
| **redis-cli** | [`skills/databases/redis.md`](skills/databases/redis.md) | Connection, key operations, debugging, persistence, cluster management |

### 🚀 Platforms & Services

| CLI | Guide | What You Get |
|-----|-------|-------------|
| **Stripe CLI** | [`skills/platforms/stripe.md`](skills/platforms/stripe.md) | Webhook testing, API debugging, fixtures, payment flow testing |
| **Sentry CLI** | [`skills/platforms/sentry.md`](skills/platforms/sentry.md) | Release management, sourcemap uploads, deploy tracking |
| **Vercel CLI** | [`skills/platforms/vercel.md`](skills/platforms/vercel.md) | Deployments, env vars, serverless functions, domains |
| **Firebase CLI** | [`skills/platforms/firebase.md`](skills/platforms/firebase.md) | Hosting deploy, Firestore rules, auth emulators, Cloud Functions |
| **flyctl** | [`skills/platforms/fly.md`](skills/platforms/fly.md) | App deployment, scaling, secrets, regions, Machines API |

Each guide follows a consistent structure:
1. **Setup & Auth** — Installation and credential configuration
2. **Core Workflows** — The 20% of commands covering 80% of usage
3. **Flag Gotchas** — Ordering traps, version quirks, surprising defaults
4. **Error Patterns** — Real error messages → real fixes
5. **Anti-Patterns** — "Never do X because Y" with safe alternatives
6. **Composability** — How to pipe this CLI with others (aws → jq → xargs)
7. **Agent Constraints** — Non-interactive alternatives, TTY workarounds

---

## 🧠 How It Works

This repo is a **single skill** following the [Agent Skills spec](https://github.com/anthropics/skills):

```
swe-cli-skills/
├── SKILL.md                      ← Agent reads this first (index + quick reference)
└── skills/
    ├── cloud/
    │   ├── INDEX.md              ← Category index
    │   ├── aws.md
    │   ├── gcloud.md
    │   └── azure.md
    ├── iac/
    │   ├── INDEX.md
    │   └── terraform.md
    ├── containers/
    │   ├── INDEX.md
    │   ├── docker.md
    │   ├── kubectl.md
    │   └── helm.md
    ├── git-vcs/
    │   ├── INDEX.md
    │   ├── git.md
    │   └── gh.md
    ├── dev-tools/
    │   ├── INDEX.md
    │   ├── jq.md
    │   ├── curl.md
    │   ├── ssh.md
    │   ├── sed.md
    │   └── make.md
    ├── package-managers/
    │   ├── INDEX.md
    │   ├── npm.md
    │   └── pip-uv.md
    ├── databases/
    │   ├── INDEX.md
    │   ├── psql.md
    │   └── redis.md
    └── platforms/
        ├── INDEX.md
        ├── stripe.md
        ├── sentry.md
        ├── vercel.md
        ├── firebase.md
        └── fly.md
```

1. Your agent sees `swe-cli-skills` in its skill index (name + description)
2. When a CLI task comes up, it reads `SKILL.md` (lightweight — just the index)
3. It loads the specific CLI guide it needs (e.g., `skills/iac/terraform.md`)
4. It executes with expert-level knowledge

**Token-efficient by design** — the agent only loads one guide (~200-400 lines) instead of the entire library.

---

## 🔥 Critical Gotchas Cheat Sheet

The highest-impact mistakes agents make — a taste of what's inside:

| CLI | Gotcha | Impact |
|-----|--------|--------|
| AWS | `--include` before `--exclude` = nothing synced | Silent data loss |
| Terraform | `terraform import` without `plan` after | Undetected drift |
| Docker | `COPY . .` before `RUN pip install` | Cache busted every build |
| kubectl | `kubectl apply` without context check | Wrong cluster deployment |
| Helm | `helm upgrade` without `--reuse-values` | Config silently reset |
| Git | `git rebase -i` in agent context | Agent hangs forever |
| SSH | `ssh user@server` without `BatchMode=yes` | Password prompt hang |
| jq | `select()` on array instead of `map(select())` | Empty/wrong output |
| curl | `-d` without `-H "Content-Type: application/json"` | Sent as form data |
| gh | `gh pr create` without `--title`/`--body` flags | Interactive prompt hang |
| psql | Script without `-v ON_ERROR_STOP=1` | Errors silently ignored |
| Redis | `KEYS *` in production | Server blocked, outage |
| gcloud | No `--project` in automation | Wrong project targeted |
| npm | `npm install` in CI/CD | Non-reproducible builds |
| sed | `sed -i` on macOS vs Linux | Different syntax, silent failure |
| make | Spaces instead of tabs in Makefile | Cryptic "missing separator" error |
| Stripe | `stripe listen` webhook secret changes on restart | Webhook verification fails |
| Sentry | Sourcemap `--url-prefix` mismatch | Sourcemaps silently don't apply |
| Vercel | `vercel` without `--prod` | Deploys preview, not production |
| Firebase | `firebase deploy` without `--only` | Deploys everything at once |
| Fly.io | `fly secrets set` one at a time | Triggers N redeploys instead of 1 |

---

## 🤝 Compatible Agents

Works with any agent that supports the [SKILL.md standard](https://github.com/anthropics/skills):

- **[AdaL](https://docs.sylph.ai/)** — Project/personal/plugin skills
- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** — Plugin marketplace
- **[OpenAI Codex](https://openai.com/codex)** — Skills directory
- **[Gemini CLI](https://github.com/google-gemini/gemini-cli)** — Agent skills
- **[GitHub Copilot](https://github.com/features/copilot)** — .github/skills
- **[Cursor](https://cursor.com)** — Custom instructions
- **[Windsurf](https://windsurf.com)** — Agent skills
- **[Aider](https://aider.chat)** — Convention files
- **[OpenCode](https://opencode.ai)** — Skills support
- Any agent that reads markdown instruction files

---

## 📖 Philosophy

1. **Workflows over reference** — "Here's how to deploy safely" not "here's every flag"
2. **Opinionated** — We encode senior engineer judgment, not neutral docs
3. **Agent-first, human-readable** — Written for LLMs to parse, useful for humans too
4. **Composability-aware** — Skills show how CLIs work together
5. **Version-tagged** — Each guide declares which CLI version it targets
6. **Battle-tested patterns** — Real gotchas from real production incidents

---

## 🗺️ Roadmap

- [x] **v0.1** — Core 10 CLIs (aws, terraform, docker, kubectl, helm, git, gh, jq, curl, ssh)
- [x] **v0.2** — 16 CLIs with category sub-indexes (gcloud, azure, npm, pip/uv, psql, redis-cli)
- [x] **v0.3** — 23 CLIs with platforms & expanded dev-tools (stripe, sentry, vercel, firebase, fly.io, sed, make)
- [ ] **v0.4** — rsync, mysql, mongo, yarn/pnpm, cargo, go, poetry, openssl
- [ ] **v1.0** — 30+ CLIs, community contributions, CI validation
- [ ] **Future** — Version-specific skill variants, auto-update from changelogs

---

## 🤲 Contributing

Every skill you add helps thousands of AI agents operate more safely and effectively.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

**Quick version:**
1. Create `skills/<category>/your-cli.md` following the guide structure
2. Add an entry to the category `INDEX.md`
3. Add an entry to `SKILL.md` and this README
4. Open a PR

**What makes a great skill:** Opinionated workflows, real gotchas you've been burned by, actual error messages with actual fixes, and non-interactive alternatives for every interactive command.

---

## 📄 License

MIT — use these skills in any project, commercial or open-source.

---

<p align="center">
  <b>⭐ Star this repo</b> if your agent has ever <code>kubectl apply</code>'d to the wrong cluster.
  <br><br>
  <i>Built by <a href="https://sylph.ai/">SylphAI</a> — the team behind <a href="https://docs.sylph.ai/">AdaL</a></i>
</p>

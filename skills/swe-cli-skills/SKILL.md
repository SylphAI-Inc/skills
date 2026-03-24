---
name: swe-cli-skills
description: "Senior engineer CLI expertise for AI agents — workflows, safety guardrails, gotchas, and anti-patterns across cloud, IaC, containers, databases, dev tools, and platforms"
---

# SWE CLI Skills

> man pages for machines — Your agent knows the commands. We teach it the workflows.

This skill provides expert-level CLI knowledge for the tools software engineers use daily. Each guide encodes **senior engineer judgment** — not reference docs, but operational workflows, safety guardrails, flag gotchas, error recovery, and composition patterns.

## When to Use This Skill

Load a specific CLI guide when:
- You need to run complex CLI operations (multi-step workflows, piped commands)
- You're unsure about flag ordering, safety checks, or non-interactive alternatives
- You encounter a CLI error and need the actual fix (not generic advice)
- You need to compose multiple CLIs together (e.g., aws → jq → xargs)

## Available CLI Guides

Guides are organized by category. Read the category index or jump directly to a CLI guide.

### ☁️ Cloud (`skills/cloud/`)

| CLI | File | Use For |
|-----|------|---------|
| **AWS CLI** | `skills/cloud/aws.md` | S3 filter ordering, IAM auth, EC2 queries, JMESPath, Lambda |
| **gcloud** | `skills/cloud/gcloud.md` | GCP project/config management, GKE, Cloud Run, IAM, logging |
| **Azure CLI** | `skills/cloud/azure.md` | Resource groups, AKS, App Service, RBAC, ARM deployments |

### 🏗️ Infrastructure as Code (`skills/iac/`)

| CLI | File | Use For |
|-----|------|---------|
| **Terraform** | `skills/iac/terraform.md` | State management, import workflows, safe apply, workspace migration |

### 🐳 Containers & Orchestration (`skills/containers/`)

| CLI | File | Use For |
|-----|------|---------|
| **Docker** | `skills/containers/docker.md` | Build cache, multi-stage builds, compose v2, cleanup, debugging |
| **kubectl** | `skills/containers/kubectl.md` | Context safety, namespace gotchas, rollout/rollback, pod debugging |
| **Helm** | `skills/containers/helm.md` | Values precedence, upgrade resets, rollback, chart debugging |

### 🔀 Git & Version Control (`skills/git-vcs/`)

| CLI | File | Use For |
|-----|------|---------|
| **Git** | `skills/git-vcs/git.md` | Non-interactive alternatives, rebase, merge, conflict resolution |
| **GitHub CLI** | `skills/git-vcs/gh.md` | PR workflows, issue management, releases, Actions |

### 🛠️ Dev Tools (`skills/dev-tools/`)

| CLI | File | Use For |
|-----|------|---------|
| **jq** | `skills/dev-tools/jq.md` | JSON filtering, select vs map, array ops, shell variable injection |
| **sed** | `skills/dev-tools/sed.md` | Stream editing, in-place substitution, macOS vs Linux portability |
| **make** | `skills/dev-tools/make.md` | Build automation, Makefile patterns, phony targets, variables |
| **curl** | `skills/dev-tools/curl.md` | Auth headers, multipart uploads, API debugging, response handling |
| **SSH/SCP** | `skills/dev-tools/ssh.md` | Tunneling, ProxyJump, key management, agent-safe patterns |

### 📦 Package Managers (`skills/package-managers/`)

| CLI | File | Use For |
|-----|------|---------|
| **npm** | `skills/package-managers/npm.md` | Dependency management, scripts, workspaces, publishing, lockfiles |
| **pip & uv** | `skills/package-managers/pip-uv.md` | Virtual envs, dependency resolution, uv acceleration, constraints |

### 🗄️ Databases (`skills/databases/`)

| CLI | File | Use For |
|-----|------|---------|
| **psql** | `skills/databases/psql.md` | Connection strings, non-interactive queries, backup/restore, meta-commands |
| **redis-cli** | `skills/databases/redis.md` | Connection, key operations, debugging, persistence, cluster management |

### 🚀 Platforms & Services (`skills/platforms/`)

| CLI | File | Use For |
|-----|------|---------|
| **Stripe CLI** | `skills/platforms/stripe.md` | Webhook testing, API debugging, fixtures, payment flow testing |
| **Sentry CLI** | `skills/platforms/sentry.md` | Release management, sourcemap uploads, deploy tracking |
| **Vercel CLI** | `skills/platforms/vercel.md` | Deployments, env vars, serverless functions, domains |
| **Firebase CLI** | `skills/platforms/firebase.md` | Hosting deploy, Firestore rules, auth emulators, Cloud Functions |
| **flyctl** | `skills/platforms/fly.md` | App deployment, scaling, secrets, regions, Machines API |

## Quick Reference: Critical Gotchas

These are the highest-impact mistakes — check the full guide for details:

- **AWS S3**: `--exclude` must come BEFORE `--include` (left-to-right evaluation)
- **Terraform**: Always `terraform plan` after `terraform import` (detects drift)
- **Docker**: Copy dependency files before source code (cache optimization)
- **kubectl**: ALWAYS verify `kubectl config current-context` before apply
- **Helm**: `helm upgrade` RESETS values not specified — use `--reuse-values`
- **Git**: Use `git --no-pager` and `--no-edit` flags (agents have no TTY)
- **SSH**: Use `BatchMode=yes` to prevent password prompt hangs
- **psql**: Always use `-v ON_ERROR_STOP=1` in scripts (psql continues after errors by default)
- **Redis**: NEVER use `KEYS *` in production — use `SCAN` instead (blocks server)
- **gcloud**: Always set `--project` explicitly in automation (don't rely on default project)
- **npm**: Use `npm ci` in CI/CD, not `npm install` (ensures reproducible builds)
- **sed**: `sed -i` behaves differently on macOS vs Linux — use `-i.bak` for portability
- **make**: Indentation MUST be real tabs, not spaces (invisible error)
- **Stripe**: `stripe listen` webhook secret changes on every restart — update your env var
- **Sentry**: Sourcemap `--url-prefix` must exactly match browser request paths
- **Vercel**: `vercel` without `--prod` deploys to preview, not production
- **Firebase**: `firebase deploy` without `--only` deploys EVERYTHING

## Token Efficiency

This skill uses a **category sub-index architecture**. Instead of loading all CLI guides at once:
1. Read this root `SKILL.md` to find the right category
2. Read only the specific CLI guide you need (e.g., `skills/cloud/aws.md`)

This keeps token usage minimal — load one guide (~200-400 lines) instead of the entire library.

## Each Guide Contains

1. **Setup & Auth** — Installation and credential configuration
2. **Core Workflows** — The 20% of commands covering 80% of usage
3. **Flag Gotchas** — Ordering traps, version quirks, surprising defaults
4. **Error Patterns** — Real error messages → real fixes
5. **Anti-Patterns** — "Never do X because Y" with safe alternatives
6. **Composability** — How to pipe this CLI with others
7. **Agent Constraints** — Non-interactive alternatives, TTY workarounds

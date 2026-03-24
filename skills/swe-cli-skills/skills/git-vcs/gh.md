---
name: gh
description: "GitHub CLI — PR workflows, issue management, release automation, repo operations, and Actions inspection"
version: "2.x"
category: git-vcs
---

# GitHub CLI (gh)

> **Official docs:** https://cli.github.com/manual/ | **Reference:** https://cli.github.com/manual/gh

The GitHub CLI brings GitHub workflows to the terminal. It handles PRs, issues, releases, Actions, and repo management without leaving the command line.

## Setup & Auth

```bash
# Installation (macOS)
brew install gh

# Verify
gh --version

# Authenticate
gh auth login  # Interactive — follow prompts

# Check auth status
gh auth status

# Set default editor (for agents, not needed if using -m/-b flags)
gh config set editor "true"  # Prevents editor from opening
```

## Core Workflows

### Workflow: Pull Requests

```bash
# Create PR from current branch
gh pr create --title "feat: add auth" --body "Adds JWT authentication"

# Create PR with auto-fill from commits
gh pr create --fill

# Create draft PR
gh pr create --title "WIP: auth" --body "Work in progress" --draft

# Create PR with reviewers and labels
gh pr create --title "feat: auth" --body "..." \
  --reviewer user1,user2 \
  --label "enhancement"

# List PRs
gh pr list
gh pr list --state all --limit 20

# View PR details
gh pr view 123
gh pr view 123 --json title,body,reviews,mergeable

# Check PR diff
gh pr diff 123

# Merge PR
gh pr merge 123 --merge  # Merge commit
gh pr merge 123 --squash  # Squash merge
gh pr merge 123 --rebase  # Rebase merge
gh pr merge 123 --auto --squash  # Auto-merge when checks pass

# Edit PR
gh pr edit 123 --title "new title" --add-label "bug"

# Review PR
gh pr review 123 --approve
gh pr review 123 --request-changes --body "Please fix X"
gh pr review 123 --comment --body "Looks good overall"
```

### Workflow: Issues

```bash
# Create issue
gh issue create --title "Bug: login fails" --body "Steps to reproduce..."

# Create with labels and assignee
gh issue create --title "Bug: login fails" \
  --body "Steps to reproduce..." \
  --label "bug" \
  --assignee "@me"

# List issues
gh issue list
gh issue list --label "bug" --state open

# View issue
gh issue view 456
gh issue view 456 --json title,body,comments

# Close issue
gh issue close 456
gh issue close 456 --comment "Fixed in #123"

# Reopen
gh issue reopen 456
```

### Workflow: Releases

```bash
# Create a release
gh release create v1.0.0 --title "Version 1.0.0" --notes "Initial release"

# Create release with auto-generated notes
gh release create v1.0.0 --generate-notes

# Create release with files
gh release create v1.0.0 ./dist/*.tar.gz --title "v1.0.0" --notes "..."

# Create draft release
gh release create v1.0.0 --draft --title "v1.0.0" --notes "..."

# List releases
gh release list

# Download release assets
gh release download v1.0.0 --dir ./downloads
```

### Workflow: Actions (CI/CD)

```bash
# List recent workflow runs
gh run list --limit 10

# View specific run
gh run view 12345

# View run logs
gh run view 12345 --log
gh run view 12345 --log-failed  # Only failed steps

# Watch a running workflow
gh run watch 12345

# Re-run failed jobs
gh run rerun 12345 --failed

# Trigger a workflow manually
gh workflow run deploy.yml --ref main -f environment=staging

# List workflows
gh workflow list
```

### Workflow: Repo Operations

```bash
# Clone
gh repo clone owner/repo

# Fork and clone
gh repo fork owner/repo --clone

# Create new repo
gh repo create my-project --public --description "My project"

# View repo info
gh repo view
gh repo view --json name,description,defaultBranchRef

# Set repo settings
gh repo edit --default-branch main
gh repo edit --enable-auto-merge --delete-branch-on-merge
```

## Flag Gotchas

### `gh pr create` body formatting

```bash
# ❌ Newlines may be lost in --body
gh pr create --title "feat" --body "Line 1\nLine 2"

# ✅ Use printf for multi-line
gh pr create --title "feat" --body "$(printf '## Summary\n\nAdded feature X\n\n## Changes\n\n- Change 1\n- Change 2')"

# ✅ Or use --body-file
echo "## Summary" > /tmp/pr-body.md
gh pr create --title "feat" --body-file /tmp/pr-body.md
```

### `--json` flag for machine-parseable output

```bash
# Human-readable (default)
gh pr view 123

# Machine-readable JSON
gh pr view 123 --json number,title,state,mergeable

# Combine with jq
gh pr list --json number,title,author --jq '.[] | [.number, .title, .author.login] | @tsv'
```

## Error Patterns

### `pull request create failed: GraphQL: No commits between main and feature`

**Cause:** Your branch has no new commits compared to the base branch.

**Fix:**
```bash
# Check if branch has diverged
git --no-pager log --oneline main..HEAD

# If empty, your branch is up to date — nothing to PR
# If you rebased, force push first
git push --force-with-lease origin feature-branch
```

### `gh auth login` fails in CI/CD

**Cause:** No interactive terminal available.

**Fix:**
```bash
# Use token-based auth
echo "$GITHUB_TOKEN" | gh auth login --with-token

# Or set environment variable
export GH_TOKEN=$GITHUB_TOKEN
# gh commands will use this automatically
```

## Anti-Patterns

### Never merge without checking CI status

```bash
# ❌ Merges even if CI is failing
gh pr merge 123 --squash

# ✅ Check status first
gh pr checks 123
gh pr merge 123 --squash  # Only if checks pass

# ✅ Or use auto-merge (waits for checks)
gh pr merge 123 --auto --squash
```

## Composability

### gh + jq

```bash
# Get all open PR authors
gh pr list --json author --jq '.[].author.login' | sort -u

# Get PRs merged this week
gh pr list --state merged --json mergedAt,title \
  --jq '.[] | select(.mergedAt > "2024-01-01") | .title'

# Get failing checks for a PR
gh pr checks 123 --json name,state \
  --jq '.[] | select(.state != "SUCCESS") | [.name, .state] | @tsv'
```

### gh + git

```bash
# Create branch, commit, push, and PR in one flow
git checkout -b feature/my-feature
# ... make changes ...
git add -A && git commit -m "feat: add feature"
git push -u origin feature/my-feature
gh pr create --fill
```

## Agent Constraints

### Non-interactive by default

```bash
# gh is mostly non-interactive when flags are provided ✅

# ❌ HANGS — interactive mode
gh pr create  # Prompts for title, body, etc.

# ✅ Provide all required fields via flags
gh pr create --title "..." --body "..."

# ❌ HANGS — auth login is interactive
gh auth login

# ✅ Token-based auth
echo "$TOKEN" | gh auth login --with-token

# ✅ Set config to prevent editor
gh config set editor "true"
gh config set prompt disabled  # Disable all interactive prompts
```

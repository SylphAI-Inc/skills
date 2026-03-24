---
name: git
description: "Git — non-interactive alternatives for agents, rebase workflows, merge strategies, conflict resolution, and history inspection"
version: "2.40+"
category: git-vcs
---

# Git

> **Official docs:** https://git-scm.com/doc | **Reference:** https://git-scm.com/docs

Git is the universal version control system. For AI agents, the critical challenge is that many git operations are **interactive** (open editors, pagers, prompts) — this skill provides non-interactive alternatives for every common workflow.

## Setup & Auth

```bash
# Verify
git --version

# Configuration
git config --global user.name "Your Name"
git config --global user.email "your@email.com"

# Default branch name
git config --global init.defaultBranch main

# Useful defaults for agents
git config --global core.pager cat  # Disable pager
git config --global pull.rebase false  # Default merge on pull
```

## Core Workflows

### Workflow: Branch and Commit

```bash
# Create and switch to new branch
git checkout -b feature/my-feature

# Stage specific files
git add src/app.py tests/test_app.py

# Stage all changes
git add -A

# Commit with message (non-interactive)
git commit -m "feat: add user authentication"

# Multi-line commit message
git commit -m "$(cat <<'EOF'
feat: add user authentication

- Added JWT token validation
- Added login/logout endpoints
- Added middleware for protected routes
EOF
)"

# Amend last commit (non-interactive)
git commit --amend --no-edit  # Keep message
git commit --amend -m "updated commit message"  # Change message
```

### Workflow: Sync with Remote

```bash
# Fetch latest
git fetch origin

# Pull with merge (default)
git pull origin main

# Pull with rebase (cleaner history)
git pull --rebase origin main

# Push
git push origin feature/my-feature

# Push and set upstream
git push -u origin feature/my-feature

# Force push (after rebase — use with care)
git push --force-with-lease origin feature/my-feature
```

### Workflow: Merge

```bash
# Merge branch into current branch (non-interactive)
git merge feature-branch --no-edit

# Merge with explicit no-fast-forward (preserves branch history)
git merge --no-ff feature-branch --no-edit

# Abort a merge with conflicts
git merge --abort
```

### Workflow: Rebase (Non-Interactive)

```bash
# Rebase current branch onto main
git rebase main

# Rebase onto specific branch
git rebase --onto main feature-base feature-branch

# Squash last N commits (non-interactive)
GIT_SEQUENCE_EDITOR="sed -i '' '2,\$s/pick/squash/'" git rebase -i HEAD~3
# On Linux (no '' after -i):
GIT_SEQUENCE_EDITOR="sed -i '2,\$s/pick/squash/'" git rebase -i HEAD~3

# Continue rebase after resolving conflicts
git add .
GIT_EDITOR=true git rebase --continue

# Abort rebase
git rebase --abort
```

### Workflow: History Inspection

```bash
# Log with no pager
git --no-pager log --oneline -20

# Log with graph
git --no-pager log --oneline --graph --all -30

# Log specific file
git --no-pager log --oneline -- path/to/file.py

# Show a specific commit
git --no-pager show abc1234

# Diff (no pager)
git --no-pager diff
git --no-pager diff --staged  # Staged changes
git --no-pager diff main..feature-branch  # Between branches

# Blame
git --no-pager blame path/to/file.py

# Search commit messages
git --no-pager log --grep="fix auth" --oneline
```

### Workflow: Stash

```bash
# Stash current changes
git stash push -m "work in progress on auth"

# List stashes
git stash list

# Apply most recent stash (keep in stash list)
git stash apply

# Pop most recent stash (remove from stash list)
git stash pop

# Apply specific stash
git stash apply stash@{2}

# Drop a stash
git stash drop stash@{0}
```

### Workflow: File Operations

```bash
# Rename (preserves history)
git mv old-name.py new-name.py

# Delete
git rm unwanted-file.py
git rm -r unwanted-directory/

# Remove from tracking but keep on disk
git rm --cached file-to-untrack.py

# Restore file to last committed version
git checkout -- path/to/file.py
# Or modern alternative (git 2.23+)
git restore path/to/file.py
```

## Flag Gotchas

### `--force` vs `--force-with-lease`

```bash
# ❌ DANGEROUS — overwrites remote unconditionally, can lose others' work
git push --force

# ✅ SAFE — fails if remote has changes you haven't fetched
git push --force-with-lease
```

### `git reset` modes

```bash
# --soft: moves HEAD, keeps changes staged
git reset --soft HEAD~1  # Undo last commit, keep changes staged

# --mixed (default): moves HEAD, unstages changes
git reset HEAD~1  # Undo last commit, keep changes in working dir

# --hard: moves HEAD, DISCARDS all changes
git reset --hard HEAD~1  # ⚠️ DESTRUCTIVE — changes are gone

# ✅ Prefer --soft for undoing commits in shared branches
```

### `checkout` vs `switch` vs `restore`

```bash
# Old way (overloaded):
git checkout -b new-branch  # Create branch
git checkout -- file.py     # Restore file (ambiguous!)

# ✅ New way (git 2.23+):
git switch -c new-branch    # Create and switch branch
git restore file.py         # Restore file (explicit!)
```

## Error Patterns

### `error: failed to push some refs`

**Cause:** Remote has commits you don't have locally.

**Fix:**
```bash
# Pull and rebase, then push
git pull --rebase origin main
git push origin main

# If you intentionally rebased:
git push --force-with-lease origin feature-branch
```

### `CONFLICT (content): Merge conflict in file.py`

**Cause:** Two branches modified the same lines.

**Fix:**
```bash
# See conflicted files
git status

# Choose one side entirely
git checkout --theirs path/to/file.py  # Accept incoming
git checkout --ours path/to/file.py    # Keep current

# After resolving all conflicts
git add .
git commit --no-edit  # For merge
# Or
GIT_EDITOR=true git rebase --continue  # For rebase
```

### `fatal: refusing to merge unrelated histories`

**Cause:** Two repos with no common ancestor (e.g., re-initialized repo).

**Fix:**
```bash
git pull origin main --allow-unrelated-histories --no-edit
```

### `error: Your local changes would be overwritten`

**Cause:** You have uncommitted changes that conflict with the operation.

**Fix:**
```bash
# Stash changes, do the operation, pop
git stash push -m "temp"
git pull --rebase origin main
git stash pop
```

## Anti-Patterns

### Never commit secrets

```bash
# ❌ Secrets in repo history forever (even after delete)
git add .env
git commit -m "add config"

# ✅ Use .gitignore
echo ".env" >> .gitignore
git add .gitignore
git commit -m "ignore env file"

# If accidentally committed, remove from history:
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env' HEAD
# Or use BFG Repo Cleaner (faster):
# bfg --delete-files .env
```

### Never rebase public/shared branches

```bash
# ❌ Rewrites history others depend on
git rebase main  # On a branch others are using

# ✅ Merge instead for shared branches
git merge main --no-edit

# ✅ Rebase is fine for YOUR feature branches before merge
git rebase main  # On your personal feature branch
```

## Composability

### Git + grep (search code history)

```bash
# Search for a string in all commits
git --no-pager log -S "function_name" --oneline

# Search with regex
git --no-pager log -G "def (process|handle)_" --oneline

# Search in diffs
git --no-pager log -p --all -S 'API_KEY' -- '*.py'
```

### Git + xargs (batch operations)

```bash
# Delete all merged branches
git branch --merged main | grep -v main | xargs -n1 git branch -d
```

## Agent Constraints

### CRITICAL: All interactive commands and alternatives

```bash
# ❌ HANGS — opens editor
git commit                    # → git commit -m "message"
git rebase -i HEAD~3          # → GIT_SEQUENCE_EDITOR="sed ..." git rebase -i HEAD~3
git merge feature             # → git merge feature --no-edit
git revert abc123             # → git revert abc123 --no-edit
git tag -a v1.0               # → git tag -a v1.0 -m "version 1.0"

# ❌ HANGS — opens pager
git log                       # → git --no-pager log
git diff                      # → git --no-pager diff
git show                      # → git --no-pager show
git blame                     # → git --no-pager blame

# ❌ HANGS — interactive staging
git add -i                    # → git add <specific-files>
git add -p                    # → git add <specific-files>

# ❌ HANGS — rebase continue opens editor
git rebase --continue         # → GIT_EDITOR=true git rebase --continue

# ✅ Set globally to prevent pager issues
export GIT_PAGER=cat
# Or use: git --no-pager <command>
```

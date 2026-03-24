---
name: pip-uv
description: "pip/uv — virtual environments, fast dependency resolution with uv, requirements management, and publishing"
version: "pip 24.x / uv 0.5+"
category: package-managers
---

# pip & uv

> **pip docs:** https://pip.pypa.io/en/stable/ | **uv docs:** https://docs.astral.sh/uv/

pip is the standard Python package installer. uv is a modern, dramatically faster replacement (10-100x) that's drop-in compatible. This guide covers both with uv as the recommended approach.

## Setup & Auth

```bash
# pip (comes with Python)
pip --version
python -m pip --version  # More reliable

# uv installation
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or: brew install uv

# Verify
uv --version
```

### Virtual Environments

```bash
# ✅ ALWAYS use virtual environments

# With uv (recommended)
uv venv                    # Creates .venv/
uv venv --python 3.12      # Specific Python version
source .venv/bin/activate

# With pip/venv
python -m venv .venv
source .venv/bin/activate

# Verify
which python  # Should show .venv path

# Deactivate
deactivate
```

## Core Workflows

### Workflow: Install Dependencies

```bash
# With uv (10-100x faster than pip)
uv pip install flask
uv pip install -r requirements.txt
uv pip install -e ".[dev]"  # Editable install with extras

# With pip
pip install flask
pip install -r requirements.txt

# Specific version
uv pip install flask==3.0.0
uv pip install "flask>=3.0,<4.0"

# Uninstall
uv pip uninstall flask

# List installed
uv pip list
uv pip list --outdated
```

### Workflow: uv Project Management (Modern)

```bash
# Initialize a new project
uv init my-project && cd my-project

# Add dependencies (updates pyproject.toml + uv.lock)
uv add flask
uv add --dev pytest ruff

# Remove
uv remove flask

# Sync (install from lockfile — deterministic)
uv sync

# Run in project environment
uv run python app.py
uv run pytest

# Update dependencies
uv lock --upgrade && uv sync
```

### Workflow: Requirements Management (Traditional)

```bash
# Compile locked requirements from .in file
uv pip compile requirements.in -o requirements.txt

# Install from locked requirements
uv pip install -r requirements.txt

# Freeze current environment
uv pip freeze > requirements.txt
```

### Workflow: uv Tool Management

```bash
# Install CLI tools globally (isolated environments)
uv tool install ruff
uv tool install black

# Run a tool without installing
uvx ruff check .
uvx black --check .

# List / upgrade
uv tool list
uv tool upgrade ruff
```

## Flag Gotchas

### `pip install` without virtual environment

```bash
# ❌ DANGEROUS — pollutes system Python
pip install flask

# ✅ Always virtual environment
uv venv && source .venv/bin/activate && uv pip install flask
```

### `pip freeze` includes everything

```bash
# ❌ Captures ALL packages including transitive deps
pip freeze > requirements.txt

# ✅ Maintain direct deps in requirements.in
uv pip compile requirements.in -o requirements.txt
```

### `uv pip` vs `uv add`

```bash
# uv pip: traditional pip-compatible (no lockfile update)
uv pip install flask

# uv add: modern project mode (updates pyproject.toml + uv.lock)
uv add flask

# ✅ Pick one workflow per project
```

## Error Patterns

### `ModuleNotFoundError: No module named 'xxx'`

**Cause:** Package not installed or wrong virtual environment.

**Fix:**
```bash
which python       # Check which Python
echo $VIRTUAL_ENV  # Check venv
source .venv/bin/activate
uv pip install missing-package
```

### `pip` is extremely slow

**Cause:** pip resolves dependencies sequentially.

**Fix:**
```bash
# ✅ Switch to uv — drop-in replacement, 10-100x faster
uv pip install -r requirements.txt
```

### `ResolutionImpossible` / dependency conflicts

**Cause:** Two packages require incompatible dependency versions.

**Fix:**
```bash
uv pip compile requirements.in --resolution=lowest
# Or pin conflicting dependency explicitly
```

## Anti-Patterns

### Never `pip install` as root/system Python

```bash
# ❌ BREAKS system tools
sudo pip install flask

# ✅ Always virtual environment
uv venv && source .venv/bin/activate && uv pip install flask
```

### Never commit .venv

```bash
echo ".venv/" >> .gitignore
# Commit requirements.txt or pyproject.toml + uv.lock instead
```

## Composability

### pip/uv + Docker

```bash
# Dockerfile with uv (fast builds)
# FROM python:3.12-slim
# COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/
# COPY requirements.txt .
# RUN uv pip install --system -r requirements.txt
# COPY . .
```

## Agent Constraints

```bash
# pip/uv are non-interactive ✅ — safe for agents
# ✅ uv run auto-creates environment if needed
uv run pytest  # Creates .venv if missing, installs deps, runs
```

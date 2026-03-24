---
name: npm
description: "npm — install vs ci, scripts, workspaces, lockfile management, publish workflows, and npx"
version: "10.x"
category: package-managers
---

# npm

> **Official docs:** https://docs.npmjs.com/ | **Reference:** https://docs.npmjs.com/cli/v10/commands

npm is the default package manager for Node.js. Key pitfalls include `install` vs `ci` confusion, lockfile drift, phantom dependencies, and script execution patterns.

## Setup & Auth

```bash
# Verify (comes with Node.js)
npm --version
node --version

# Login to npm registry
npm login

# Check who you're logged in as
npm whoami

# Set registry (for private registries)
npm config set registry https://registry.npmjs.org/
npm config set @myorg:registry https://npm.pkg.github.com/
```

## Core Workflows

### Workflow: Install Dependencies

```bash
# Install from package.json (adds/updates lockfile)
npm install

# ✅ CI/CD: Clean install from lockfile (faster, deterministic)
npm ci

# Install a specific package
npm install express
npm install -D jest  # Dev dependency
npm install -g typescript  # Global

# Install exact version
npm install express@4.18.2

# Uninstall
npm uninstall express

# Check for outdated packages
npm outdated

# Update packages (respects semver ranges in package.json)
npm update
```

### Workflow: Scripts

```bash
# Run a script defined in package.json
npm run build
npm run test
npm run dev

# Shorthand for common scripts
npm test      # = npm run test
npm start     # = npm run start

# Run with arguments
npm run test -- --watch --coverage

# List available scripts
npm run
```

### Workflow: npx (Execute Packages)

```bash
# Run a package without installing globally
npx create-react-app my-app
npx ts-node script.ts
npx eslint --fix .

# Run specific version
npx -p typescript@5.0 tsc --version
```

### Workflow: Workspaces (Monorepo)

```bash
# Run script in specific workspace
npm run build -w packages/core
npm run test -w packages/api

# Run script in all workspaces
npm run build --workspaces

# Add dependency to specific workspace
npm install express -w packages/api
```

### Workflow: Publish

```bash
# Check what will be published
npm pack --dry-run

# Bump version
npm version patch  # 1.0.0 → 1.0.1
npm version minor  # 1.0.0 → 1.1.0
npm version major  # 1.0.0 → 2.0.0

# Publish
npm publish
npm publish --access public  # Scoped package as public
npm publish --tag beta       # With tag
```

## Flag Gotchas

### `npm install` vs `npm ci`

```bash
# ❌ WRONG in CI/CD — may modify lockfile, slower
npm install

# ✅ CORRECT in CI/CD — installs exactly from lockfile, clean slate
npm ci

# Key differences:
# install: reads package.json, may update package-lock.json
# ci: reads package-lock.json ONLY, fails if out of sync
# ci: deletes node_modules before installing
# ci: significantly faster in CI environments
```

### `--save` is default since npm 5

```bash
# ❌ REDUNDANT — --save is the default
npm install --save express

# ✅ CLEANER
npm install express        # dependencies
npm install -D jest        # devDependencies
npm install --save-exact express  # Pin exact version (no ^)
```

## Error Patterns

### `ERESOLVE unable to resolve dependency tree`

**Cause:** Peer dependency conflicts between packages.

**Fix:**
```bash
npm install --legacy-peer-deps  # Force resolution
# ✅ Best: fix the actual conflict in package.json
```

### `EACCES: permission denied`

**Cause:** Global packages installed with wrong permissions.

**Fix:**
```bash
# ❌ NEVER use sudo with npm
# ✅ Fix npm prefix
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
# Add to PATH: export PATH=~/.npm-global/bin:$PATH
```

## Anti-Patterns

### Never commit `node_modules`

```bash
echo "node_modules/" >> .gitignore
# Commit package-lock.json instead
```

### Never use `npm install` in Dockerfiles

```bash
# ❌ Slower, may modify lockfile
RUN npm install

# ✅ Deterministic, faster
COPY package.json package-lock.json ./
RUN npm ci --only=production
```

## Composability

### npm + jq

```bash
cat package-lock.json | jq '.packages["node_modules/express"].version'
```

## Agent Constraints

```bash
# ❌ HANGS — interactive init/login
npm init
npm login

# ✅ Non-interactive
npm init -y
echo "//registry.npmjs.org/:_authToken=$NPM_TOKEN" >> ~/.npmrc
npx --yes create-react-app my-app
```

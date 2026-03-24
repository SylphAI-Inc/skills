# Vercel CLI

## Setup & Auth

```bash
# Install
npm i -g vercel

# Login (opens browser)
vercel login

# Login with token (CI/CD)
export VERCEL_TOKEN=xxx
vercel --token $VERCEL_TOKEN

# Check current user/team
vercel whoami

# Switch team
vercel switch my-team

# Link project to Vercel
vercel link
```

## Deployments

```bash
# Deploy (preview — default)
vercel

# Deploy to production
vercel --prod

# Deploy without prompts (CI/CD)
vercel --yes --prod

# Deploy specific directory
vercel ./dist --prod

# Deploy with environment
vercel --env NODE_ENV=production --prod

# Deploy and get URL only (for scripts)
vercel --prod 2>&1 | tail -1

# Force new deployment (skip cache)
vercel --force

# List deployments
vercel ls

# Inspect a deployment
vercel inspect <deployment-url>

# Redeploy a previous deployment
vercel redeploy <deployment-url>
```

### Build & Output Settings

```bash
# Override build command
vercel --build-env CI=true

# Skip build step (pre-built output)
vercel --prebuilt

# For monorepos — set root directory
vercel --cwd packages/web
```

## Environment Variables

```bash
# Add env var (interactive)
vercel env add MY_VAR

# Add env var non-interactively
printf "my-value" | vercel env add MY_VAR production

# Add to multiple environments
printf "my-value" | vercel env add MY_VAR production preview development

# List env vars
vercel env ls

# Pull env vars to local .env file
vercel env pull .env.local

# Remove env var
vercel env rm MY_VAR production
```

> **⚠️ `vercel env pull`** creates `.env.local` with production values. Add `.env.local` to `.gitignore`.

## Domains

```bash
# Add a domain
vercel domains add example.com

# List domains
vercel domains ls

# Inspect domain (DNS, SSL status)
vercel domains inspect example.com

# Remove domain
vercel domains rm example.com

# Add domain alias to deployment
vercel alias <deployment-url> example.com

# List aliases
vercel alias ls
```

## Serverless Functions

```bash
# Dev server (runs functions locally)
vercel dev

# Dev server on specific port
vercel dev --listen 3001

# Logs from deployed functions
vercel logs <deployment-url>

# Stream logs in real-time
vercel logs <deployment-url> --follow

# Filter by function
vercel logs <deployment-url> --output raw | grep "api/users"
```

## Projects

```bash
# List projects
vercel project ls

# Remove a project
vercel project rm my-project

# Add project setting
vercel project add-env MY_VAR production
```

## Common CI/CD Patterns

### GitHub Actions

```yaml
- name: Deploy to Vercel
  env:
    VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
    VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
    VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
  run: |
    npm i -g vercel
    vercel pull --yes --environment=production
    vercel build --prod
    vercel deploy --prebuilt --prod
```

### Preview Deploys for PRs

```bash
# Deploy preview and capture URL
DEPLOY_URL=$(vercel --yes --token $VERCEL_TOKEN 2>&1 | tail -1)
# Post URL as PR comment via gh cli
gh pr comment $PR_NUMBER --body "Preview: $DEPLOY_URL"
```

## Gotchas

1. **`vercel` without `--prod` = preview** — Default deploys are preview (unique URL, not production). Always use `--prod` for production.
2. **`vercel dev` needs linking** — Run `vercel link` first, or it won't know your project settings.
3. **Env vars are environment-scoped** — A var set for `production` won't exist in `preview` or `development`. Set for all three if needed.
4. **`vercel env pull` overwrites** — It replaces your local `.env.local` without confirmation.
5. **Function size limits** — Serverless functions have a 50MB compressed limit (250MB uncompressed). Edge functions are 4MB.
6. **Build cache** — Vercel caches `node_modules` between builds. Use `--force` if you need a clean build.
7. **Monorepo root directory** — If your app is in a subdirectory, set the root directory in project settings or use `--cwd`.

# Sentry CLI (sentry-cli)

## Setup & Auth

```bash
# Install
brew install getsentry/tools/sentry-cli   # macOS
npm install -g @sentry/cli                 # npm
curl -sL https://sentry.io/get-cli/ | sh  # Script

# Login (stores token in ~/.sentryclirc)
sentry-cli login

# Or set token via environment (CI/CD preferred)
export SENTRY_AUTH_TOKEN=sntrys_xxx
export SENTRY_ORG=my-org
export SENTRY_PROJECT=my-project

# Verify setup
sentry-cli info
```

### Configuration File (~/.sentryclirc or .sentryclirc in project)

```ini
[auth]
token=sntrys_xxx

[defaults]
org=my-org
project=my-project
url=https://sentry.io/  # or self-hosted URL
```

> **⚠️ Use env vars in CI/CD, not config files.** Never commit `.sentryclirc` with tokens.

## Release Management

```bash
# Create a new release
sentry-cli releases new v1.2.3

# Associate commits (auto-detect from git)
sentry-cli releases set-commits v1.2.3 --auto

# Associate commits from specific repo
sentry-cli releases set-commits v1.2.3 --commit "org/repo@from_sha..to_sha"

# Finalize release (marks as deployed)
sentry-cli releases finalize v1.2.3

# One-liner: create + set commits + finalize
sentry-cli releases new v1.2.3 && \
sentry-cli releases set-commits v1.2.3 --auto && \
sentry-cli releases finalize v1.2.3

# Delete a release
sentry-cli releases delete v1.2.3

# List releases
sentry-cli releases list
```

### Propose Version (auto-generate version string)

```bash
# Use git SHA as version
VERSION=$(sentry-cli releases propose-version)
sentry-cli releases new "$VERSION"

# Common patterns:
# - Git SHA: abc123def
# - Package version: 1.2.3
# - Build ID: build-2024-01-15-abc123
```

## Sourcemap Uploads

```bash
# Upload sourcemaps for a release
sentry-cli sourcemaps upload --release v1.2.3 ./dist

# With URL prefix (must match how files are served)
sentry-cli sourcemaps upload --release v1.2.3 \
  --url-prefix "~/static/js" \
  ./build/static/js

# Upload with dist identifier (for multi-deployment)
sentry-cli sourcemaps upload --release v1.2.3 \
  --dist 1 \
  ./dist

# Validate sourcemaps before upload
sentry-cli sourcemaps explain --release v1.2.3 --org my-org --project my-project

# Upload with rewrite (fix embedded source references)
sentry-cli sourcemaps upload --release v1.2.3 \
  --rewrite \
  ./dist

# Delete sourcemaps for a release
sentry-cli releases files v1.2.3 delete --all
```

### URL Prefix Rules

| Your setup | URL prefix | Example |
|------------|-----------|---------|
| Files at root | `~/` | `~/main.js` → `https://example.com/main.js` |
| Files in `/static/js/` | `~/static/js` | `~/static/js/main.js` → `https://example.com/static/js/main.js` |
| Files on CDN | `https://cdn.example.com/` | Full URL match |
| React/CRA build | `~/static/js` | Standard Create React App |
| Next.js | `~/_next` | Standard Next.js build |

> **⚠️ URL prefix must match** how the browser requests the file. Mismatched prefixes = sourcemaps silently don't apply.

## Deploy Tracking

```bash
# Create a deploy for a release
sentry-cli releases deploys v1.2.3 new -e production

# With timestamp
sentry-cli releases deploys v1.2.3 new \
  -e production \
  --started "$(date -u +%s)" \
  --finished "$(date -u +%s)"

# Deploy to staging
sentry-cli releases deploys v1.2.3 new -e staging

# List deploys
sentry-cli releases deploys v1.2.3 list
```

## Debug Information Files (dSYMs, ProGuard)

```bash
# Upload iOS dSYMs
sentry-cli debug-files upload --include-sources path/to/dSYMs

# Upload Android ProGuard mappings
sentry-cli upload-proguard --android-manifest app/build/AndroidManifest.xml \
  app/build/outputs/mapping/release/mapping.txt

# Check uploaded debug files
sentry-cli debug-files list

# Check if debug files are needed
sentry-cli debug-files check path/to/executable
```

## Monitors (Cron Job Monitoring)

```bash
# Wrap a cron job with Sentry monitoring
sentry-cli monitors run my-cron-slug -- /path/to/script.sh

# Example in crontab:
# */5 * * * * sentry-cli monitors run data-sync -- python sync.py

# Create a monitor
sentry-cli monitors create my-monitor --schedule "0 * * * *" --timezone UTC

# List monitors
sentry-cli monitors list
```

## Common CI/CD Patterns

### GitHub Actions

```yaml
- name: Create Sentry release
  env:
    SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
    SENTRY_ORG: my-org
    SENTRY_PROJECT: my-project
  run: |
    VERSION=$(sentry-cli releases propose-version)
    sentry-cli releases new "$VERSION"
    sentry-cli releases set-commits "$VERSION" --auto
    sentry-cli sourcemaps upload --release "$VERSION" \
      --url-prefix "~/static/js" \
      ./build/static/js
    sentry-cli releases finalize "$VERSION"
    sentry-cli releases deploys "$VERSION" new -e production
```

### Docker Build Integration

```bash
# Upload sourcemaps during build, then delete from image
RUN sentry-cli sourcemaps upload --release $VERSION ./dist && \
    rm -f ./dist/**/*.map
```

## Gotchas

1. **URL prefix mismatch** — The #1 reason sourcemaps don't work. The `--url-prefix` must exactly match how browsers request the file. Use `sentry-cli sourcemaps explain` to debug.
2. **Release must be finalized** — Sourcemaps uploaded to a non-finalized release may not apply. Always call `releases finalize`.
3. **`--auto` commits needs repo access** — `set-commits --auto` requires the Sentry GitHub/GitLab integration to be configured, or it silently does nothing.
4. **Sourcemaps must include `sourcesContent`** — If your build strips source content, Sentry can't show source context. Check your bundler config.
5. **Auth token scope** — CLI tokens need `project:releases`, `org:read` at minimum. For sourcemaps, also need `project:write`.
6. **Self-hosted URL** — If using self-hosted Sentry, set `SENTRY_URL` env var or `url` in `.sentryclirc`. Default is `https://sentry.io/`.
7. **Rate limits on uploads** — Large sourcemap uploads (100+ files) can hit rate limits. Use `--wait` flag or upload in batches.
8. **`propose-version` uses HEAD SHA** — It returns the current git HEAD SHA. Make sure your CI checkout has the correct commit.

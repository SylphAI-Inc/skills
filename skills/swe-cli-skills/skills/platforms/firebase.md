# Firebase CLI

## Setup & Auth

```bash
# Install
npm install -g firebase-tools

# Login (opens browser)
firebase login

# Login in CI/CD (non-interactive)
firebase login:ci  # generates a token
export FIREBASE_TOKEN=xxx
# Or use service account
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json

# Check current user
firebase login:list

# Initialize project
firebase init

# Initialize specific features
firebase init hosting firestore functions

# Use a specific project
firebase use my-project-id

# List projects
firebase projects:list

# Add project alias
firebase use --add  # interactive alias setup
```

## Hosting

```bash
# Deploy hosting only
firebase deploy --only hosting

# Deploy specific site (multi-site)
firebase deploy --only hosting:my-site

# Preview channel (temporary preview URL)
firebase hosting:channel:deploy preview-branch
firebase hosting:channel:deploy pr-123 --expires 7d

# List preview channels
firebase hosting:channel:list

# Delete preview channel
firebase hosting:channel:delete preview-branch

# Disable hosting (take site offline)
firebase hosting:disable
```

## Firestore

```bash
# Deploy Firestore rules
firebase deploy --only firestore:rules

# Deploy Firestore indexes
firebase deploy --only firestore:indexes

# Export Firestore data
gcloud firestore export gs://my-bucket/backup

# Import Firestore data
gcloud firestore import gs://my-bucket/backup

# Delete all documents in a collection (use with caution)
firebase firestore:delete --all-collections
firebase firestore:delete users --recursive
```

## Cloud Functions

```bash
# Deploy all functions
firebase deploy --only functions

# Deploy specific function
firebase deploy --only functions:myFunction

# Deploy function group
firebase deploy --only functions:group-name

# View function logs
firebase functions:log

# View logs for specific function
firebase functions:log --only myFunction

# Stream logs
firebase functions:log --follow

# Delete a function
firebase functions:delete myFunction

# Set function config/env
firebase functions:config:set service.api_key="xxx"
firebase functions:config:get
```

## Emulators (Local Development)

```bash
# Start all configured emulators
firebase emulators:start

# Start specific emulators
firebase emulators:start --only auth,firestore,functions

# Start with data import
firebase emulators:start --import ./emulator-data

# Export emulator data on shutdown
firebase emulators:start --export-on-exit ./emulator-data

# Run tests against emulators
firebase emulators:exec "npm test"

# Emulator UI (auto-opens)
# Default: http://localhost:4000
```

### Emulator Ports (Defaults)

| Service | Port |
|---------|------|
| Auth | 9099 |
| Firestore | 8080 |
| Functions | 5001 |
| Hosting | 5000 |
| Pub/Sub | 8085 |
| Storage | 9199 |
| Emulator UI | 4000 |

## Authentication

```bash
# Export auth users
firebase auth:export users.json

# Import auth users
firebase auth:import users.json --hash-algo=BCRYPT
```

## Storage

```bash
# Deploy storage rules
firebase deploy --only storage

# Upload file via gsutil
gsutil cp local-file.png gs://my-bucket/path/
```

## Remote Config

```bash
# Get current config
firebase remoteconfig:get -o config.json

# Deploy config
firebase remoteconfig:rollback -v 5  # rollback to version 5
```

## Common Patterns

### Selective Deploys

```bash
# Deploy only what changed (faster CI/CD)
firebase deploy --only hosting,functions:api
firebase deploy --only firestore:rules,firestore:indexes
```

### Multi-Environment

```bash
# Set up project aliases
firebase use --add  # then choose "staging" alias
firebase use --add  # then choose "production" alias

# Deploy to staging
firebase use staging && firebase deploy

# Deploy to production
firebase use production && firebase deploy

# One-liner
firebase deploy --project my-project-prod
```

## Gotchas

1. **`firebase deploy` deploys EVERYTHING** — Without `--only`, it deploys hosting, functions, rules, AND indexes. Use `--only` for targeted deploys.
2. **Functions cold starts** — First invocation after deploy is slow. Use `--only functions:specificFn` to minimize redeploys.
3. **Emulator data is ephemeral** — Data is lost on restart unless you use `--export-on-exit` and `--import`.
4. **`firebase init` overwrites** — Running `init` again can overwrite `firestore.rules`, `firebase.json`, etc. Back up first.
5. **Functions runtime** — Default is Node.js 18. Set in `functions/package.json` under `engines.node`. Mismatch = deploy failure.
6. **Hosting preview channels expire** — Default is 7 days. Set `--expires` explicitly for longer previews.
7. **`firebase use` is sticky** — It writes to `.firebaserc`. Committing this file affects all collaborators. Use `--project` flag in CI/CD instead.
8. **Service account vs CLI token** — `FIREBASE_TOKEN` (from `login:ci`) is deprecated for CI/CD. Use `GOOGLE_APPLICATION_CREDENTIALS` with a service account key.

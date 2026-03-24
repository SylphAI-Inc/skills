---
name: gcloud
description: "Google Cloud CLI — project/config management, GKE, Cloud Run, IAM, gsutil, and multi-account workflows"
version: "400+"
category: cloud
---

# Google Cloud CLI (gcloud)

> **Official docs:** https://cloud.google.com/sdk/docs | **Reference:** https://cloud.google.com/sdk/gcloud/reference

The Google Cloud CLI manages GCP resources. The biggest pitfalls are project/config confusion (operating on the wrong project), gcloud vs gsutil distinction, and auth mode differences between user and service accounts.

## Setup & Auth

```bash
# Installation (macOS)
brew install --cask google-cloud-sdk

# Verify
gcloud version

# Initialize (interactive — sets project, region, zone)
gcloud init

# Auth for user accounts
gcloud auth login

# Auth for service accounts (CI/CD)
gcloud auth activate-service-account --key-file=key.json

# Application Default Credentials (for SDKs/Terraform)
gcloud auth application-default login

# Verify current auth
gcloud auth list
```

### Configuration Management

```bash
# View current config
gcloud config list

# Set default project
gcloud config set project my-project-id

# Set default region/zone
gcloud config set compute/region us-central1
gcloud config set compute/zone us-central1-a

# Named configurations (switch between projects/accounts)
gcloud config configurations create staging
gcloud config configurations activate staging
gcloud config set project staging-project
gcloud config set account staging@company.iam.gserviceaccount.com

# List configurations
gcloud config configurations list

# Switch back
gcloud config configurations activate default
```

## Core Workflows

### Workflow: Compute Engine (VMs)

```bash
# List instances
gcloud compute instances list

# Create instance
gcloud compute instances create my-vm \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=debian-12 \
  --image-project=debian-cloud

# SSH into instance
gcloud compute ssh my-vm --zone=us-central1-a

# Stop/Start
gcloud compute instances stop my-vm --zone=us-central1-a
gcloud compute instances start my-vm --zone=us-central1-a

# Delete
gcloud compute instances delete my-vm --zone=us-central1-a --quiet
```

### Workflow: GKE (Kubernetes)

```bash
# Create cluster
gcloud container clusters create my-cluster \
  --zone=us-central1-a \
  --num-nodes=3 \
  --machine-type=e2-standard-4

# Get credentials (configures kubectl)
gcloud container clusters get-credentials my-cluster --zone=us-central1-a

# List clusters
gcloud container clusters list

# Resize
gcloud container clusters resize my-cluster --num-nodes=5 --zone=us-central1-a --quiet

# Delete
gcloud container clusters delete my-cluster --zone=us-central1-a --quiet
```

### Workflow: Cloud Run

```bash
# Deploy from source
gcloud run deploy my-service \
  --source=. \
  --region=us-central1 \
  --allow-unauthenticated

# Deploy from image
gcloud run deploy my-service \
  --image=gcr.io/my-project/my-image:latest \
  --region=us-central1 \
  --set-env-vars="KEY=value,DB_URL=postgres://..."

# List services
gcloud run services list --region=us-central1

# View logs
gcloud run services logs read my-service --region=us-central1 --limit=50

# Set traffic splitting (canary)
gcloud run services update-traffic my-service \
  --region=us-central1 \
  --to-revisions=my-service-00002=10,my-service-00001=90
```

### Workflow: Cloud Storage (gsutil)

```bash
# ⚠️ Cloud Storage uses gsutil or gcloud storage, NOT gcloud directly

# List buckets
gcloud storage ls
# or: gsutil ls

# Upload file
gcloud storage cp local-file.txt gs://my-bucket/path/
# or: gsutil cp local-file.txt gs://my-bucket/path/

# Sync directory
gcloud storage rsync ./local-dir gs://my-bucket/path/ --recursive
# or: gsutil -m rsync -r ./local-dir gs://my-bucket/path/

# Download
gcloud storage cp gs://my-bucket/path/file.txt ./local-file.txt

# Make public
gcloud storage objects update gs://my-bucket/file.txt --add-acl-grant=entity=allUsers,role=READER
```

### Workflow: IAM

```bash
# List service accounts
gcloud iam service-accounts list

# Create service account
gcloud iam service-accounts create my-sa \
  --display-name="My Service Account"

# Grant role to service account
gcloud projects add-iam-policy-binding my-project \
  --member="serviceAccount:my-sa@my-project.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

# Create key for service account
gcloud iam service-accounts keys create key.json \
  --iam-account=my-sa@my-project.iam.gserviceaccount.com

# View current project IAM policy
gcloud projects get-iam-policy my-project
```

## Flag Gotchas

### `gcloud` vs `gsutil` vs `gcloud storage`

```bash
# ❌ WRONG — gcloud doesn't handle storage directly (legacy confusion)
gcloud cp file.txt gs://bucket/  # Doesn't exist

# ✅ Use gcloud storage (modern) or gsutil (legacy but still works)
gcloud storage cp file.txt gs://bucket/
gsutil cp file.txt gs://bucket/

# gcloud storage is the recommended replacement for gsutil
# gsutil still works and has some features gcloud storage doesn't yet
```

### `--project` override vs config

```bash
# ❌ DANGEROUS — forgets which project is active
gcloud compute instances list  # Which project?

# ✅ Always verify or specify explicitly
gcloud config get-value project  # Check first
gcloud compute instances list --project=my-project  # Explicit
```

### `--quiet` / `-q` suppresses confirmation prompts

```bash
# ❌ HANGS for agents — asks "Do you want to continue?"
gcloud container clusters delete my-cluster

# ✅ Use --quiet to suppress prompts
gcloud container clusters delete my-cluster --zone=us-central1-a --quiet
```

### `--format` for machine-readable output

```bash
# Default: human-readable table
gcloud compute instances list

# JSON (for jq piping)
gcloud compute instances list --format=json

# Specific fields
gcloud compute instances list --format="table(name,zone,status,networkInterfaces[0].accessConfigs[0].natIP)"

# Value only (for scripting)
gcloud compute instances list --format="value(name)" --filter="status=RUNNING"
```

## Error Patterns

### `ERROR: (gcloud) The project property is set to the empty string`

**Cause:** No default project configured.

**Fix:**
```bash
gcloud config set project my-project-id
# Or specify per-command: --project=my-project-id
```

### `ERROR: (gcloud.auth) Your current active account does not have any valid credentials`

**Cause:** Auth tokens expired.

**Fix:**
```bash
# For user accounts
gcloud auth login

# For service accounts
gcloud auth activate-service-account --key-file=key.json

# For Application Default Credentials
gcloud auth application-default login
```

### `HttpError 403: Required permission`

**Cause:** Account doesn't have the necessary IAM role.

**Fix:**
```bash
# Check who you are
gcloud auth list
gcloud config get-value account

# Check what roles you have
gcloud projects get-iam-policy my-project \
  --flatten="bindings[].members" \
  --filter="bindings.members:$(gcloud config get-value account)" \
  --format="table(bindings.role)"
```

## Anti-Patterns

### Never use user credentials in CI/CD

```bash
# ❌ INSECURE — user tokens expire and aren't auditable
gcloud auth login  # In CI pipeline

# ✅ Use service account with Workload Identity Federation
gcloud auth login --cred-file=credentials.json  # WIF
# Or traditional service account key (less preferred)
gcloud auth activate-service-account --key-file=key.json
```

### Never leave default project unset

```bash
# ❌ DANGEROUS — commands may hit the wrong project
gcloud compute instances delete my-vm  # Which project?!

# ✅ Use named configurations per environment
gcloud config configurations activate production
gcloud config get-value project  # Verify
```

## Composability

### gcloud + jq

```bash
# Get all running VMs with their IPs
gcloud compute instances list --format=json | \
  jq -r '.[] | select(.status == "RUNNING") | [.name, .networkInterfaces[0].networkIP] | @tsv'

# Get GKE cluster endpoints
gcloud container clusters list --format=json | \
  jq -r '.[] | [.name, .endpoint, .currentNodeCount] | @tsv'
```

### gcloud + kubectl

```bash
# Switch to a GKE cluster and verify
gcloud container clusters get-credentials my-cluster --zone=us-central1-a
kubectl config current-context
kubectl get nodes
```

### gcloud + terraform

```bash
# Set ADC for Terraform
gcloud auth application-default login
# Terraform automatically uses Application Default Credentials
terraform plan
```

## Agent Constraints

### Non-interactive operations

```bash
# ❌ HANGS — interactive prompts
gcloud init                    # → Use gcloud config set commands
gcloud auth login             # → Use service account key
gcloud container clusters delete  # → Add --quiet

# ✅ Always use --quiet for destructive operations
gcloud compute instances delete my-vm --zone=us-central1-a --quiet

# ✅ Use --format for parseable output
gcloud compute instances list --format=json

# ✅ Disable prompts globally
gcloud config set core/disable_prompts true
```

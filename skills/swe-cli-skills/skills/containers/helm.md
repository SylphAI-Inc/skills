---
name: helm
description: "Helm — chart management, values precedence, upgrade workflows, rollback, and debugging releases"
version: "3.x"
category: containers
---

# Helm

> **Official docs:** https://helm.sh/docs/ | **Reference:** https://helm.sh/docs/helm/

Helm is the package manager for Kubernetes. The biggest pitfalls are values precedence during upgrades (losing custom config), release state management, and debugging failed deployments.

## Setup & Auth

```bash
# Installation (macOS)
brew install helm

# Verify
helm version

# Add common repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
```

## Core Workflows

### Workflow: Install a Chart

```bash
# Search for charts
helm search repo nginx
helm search hub nginx  # Search Artifact Hub

# Show chart values (what's configurable)
helm show values bitnami/nginx > values.yaml

# Install with custom values
helm install my-release bitnami/nginx \
  -n my-namespace \
  -f values.yaml \
  --set replicaCount=3

# Dry-run first (validates without installing)
helm install my-release bitnami/nginx \
  -n my-namespace \
  -f values.yaml \
  --dry-run
```

### Workflow: Safe Upgrade (CRITICAL)

```bash
# 1. Check current values
helm get values my-release -n my-namespace

# 2. Diff before upgrade (requires helm-diff plugin)
helm diff upgrade my-release bitnami/nginx \
  -n my-namespace \
  -f values.yaml \
  --set image.tag=1.25

# 3. Upgrade with explicit values
helm upgrade my-release bitnami/nginx \
  -n my-namespace \
  -f values.yaml \
  --set image.tag=1.25

# 4. Verify
helm status my-release -n my-namespace
kubectl get pods -n my-namespace -l app.kubernetes.io/instance=my-release
```

### Workflow: Rollback

```bash
# List release history
helm history my-release -n my-namespace

# Rollback to previous version
helm rollback my-release -n my-namespace

# Rollback to specific revision
helm rollback my-release 3 -n my-namespace

# Verify
helm status my-release -n my-namespace
```

### Workflow: Debugging

```bash
# Render templates locally (see what YAML will be applied)
helm template my-release bitnami/nginx -f values.yaml

# Render with debug info
helm template my-release bitnami/nginx -f values.yaml --debug

# Get all resources from a release
helm get manifest my-release -n my-namespace

# Get release notes
helm get notes my-release -n my-namespace

# Test a release (runs test pods)
helm test my-release -n my-namespace
```

## Flag Gotchas

### `helm upgrade` RESETS values not specified (CRITICAL)

```bash
# ❌ DANGEROUS — custom values from install/previous upgrade are LOST
helm upgrade my-release bitnami/nginx --set image.tag=v2

# ✅ CORRECT — reuse existing values and override specific ones
helm upgrade my-release bitnami/nginx \
  --reuse-values \
  --set image.tag=v2

# ✅ HYBRID — reset to chart defaults, then apply last release's values + overrides
helm upgrade my-release bitnami/nginx \
  --reset-then-reuse-values \
  --set image.tag=v2

# ✅ BEST — always provide the full values file
helm upgrade my-release bitnami/nginx \
  -f values.yaml \
  --set image.tag=v2
```

### `--set` vs `-f` precedence

```bash
# Values are applied in this order (last wins):
# 1. Chart default values.yaml
# 2. -f files (in order specified)
# 3. --set flags (in order specified)

# ✅ --set overrides -f which overrides defaults
helm install my-release bitnami/nginx \
  -f base-values.yaml \
  -f env-values.yaml \
  --set replicaCount=5  # This wins for replicaCount
```

### `--wait` blocks until resources are ready

```bash
# Without --wait: returns immediately after submitting to k8s
helm install my-release bitnami/nginx

# With --wait: blocks until pods are Ready (useful in CI/CD)
helm install my-release bitnami/nginx --wait --timeout 5m

# ⚠️ If pods never become ready, --wait will timeout and FAIL the release
```

## Error Patterns

### `Error: UPGRADE FAILED: another operation is in progress`

**Cause:** A previous helm operation crashed, leaving the release in a pending state.

**Fix:**
```bash
# Check release status
helm status my-release -n my-namespace
helm history my-release -n my-namespace

# If stuck in pending-install/pending-upgrade:
helm rollback my-release 0 -n my-namespace  # Rollback to last successful

# Nuclear option: uninstall and reinstall
helm uninstall my-release -n my-namespace
helm install my-release bitnami/nginx -f values.yaml -n my-namespace
```

### `Error: rendered manifests contain a resource that already exists`

**Cause:** Resources exist in the cluster but aren't managed by this Helm release.

**Fix:**
```bash
# Option 1: Adopt existing resources
kubectl annotate <resource-type> <name> meta.helm.sh/release-name=my-release
kubectl annotate <resource-type> <name> meta.helm.sh/release-namespace=my-namespace
kubectl label <resource-type> <name> app.kubernetes.io/managed-by=Helm

# Option 2: Delete conflicting resources first
kubectl delete <resource-type> <name> -n my-namespace
# Then retry helm install
```

### `Error: chart requires kubeVersion >=1.25`

**Cause:** Chart needs a newer Kubernetes version than your cluster.

**Fix:**
```bash
# Check your cluster version
kubectl version

# Use an older chart version that supports your k8s
helm search repo bitnami/nginx --versions | head -20
helm install my-release bitnami/nginx --version 13.2.0
```

## Anti-Patterns

### Never upgrade without knowing current values

```bash
# ❌ Upgrades blindly — may lose custom configuration
helm upgrade my-release bitnami/nginx --set newFlag=true

# ✅ Export current values, review, then upgrade
helm get values my-release -n my-namespace -o yaml > current-values.yaml
# Review and merge your changes
helm upgrade my-release bitnami/nginx -f current-values.yaml --set newFlag=true
```

### Never skip `helm repo update` before operations

```bash
# ❌ May install outdated chart versions
helm install my-release bitnami/nginx

# ✅ Always update repo index first
helm repo update
helm install my-release bitnami/nginx
```

## Composability

### Helm + kubectl

```bash
# Check pods from a specific release
kubectl get pods -n my-namespace -l app.kubernetes.io/instance=my-release

# View rendered resources
helm get manifest my-release -n my-namespace | kubectl get -f - -o wide
```

### Helm + jq

```bash
# Get all release names and statuses
helm list -A -o json | jq -r '.[] | [.name, .namespace, .status] | @tsv'

# Get chart versions across namespaces
helm list -A -o json | jq -r '.[] | [.name, .chart, .app_version] | @tsv'
```

## Agent Constraints

### Non-interactive operations

```bash
# All Helm commands are non-interactive by default ✅
# But always set timeouts for --wait operations
helm upgrade my-release bitnami/nginx --wait --timeout 5m

# Force replacement (if resources are stuck)
helm upgrade my-release bitnami/nginx --force
```

### No pager

```bash
# Helm doesn't use a pager, but template output can be long
helm template my-release bitnami/nginx | head -100  # Preview
helm get manifest my-release | cat  # Force no-pager for pipe
```

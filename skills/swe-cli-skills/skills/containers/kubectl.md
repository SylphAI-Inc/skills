---
name: kubectl
description: "kubectl — context safety, namespace management, rollout/rollback, debugging pods, and resource inspection"
version: "1.28+"
category: containers
---

# kubectl

> **Official docs:** https://kubernetes.io/docs/reference/kubectl/ | **Cheat sheet:** https://kubernetes.io/docs/reference/kubectl/cheatsheet/

kubectl is the CLI for Kubernetes cluster management. The biggest risks are deploying to the wrong cluster/namespace and destructive operations without dry-run verification.

## Setup & Auth

```bash
# Installation (macOS)
brew install kubectl

# Verify
kubectl version --client

# Configure cluster access (EKS)
aws eks update-kubeconfig --name my-cluster --region us-east-1

# Configure cluster access (GKE)
gcloud container clusters get-credentials my-cluster --region us-central1

# View current config
kubectl config view --minify
```

### Context Management (CRITICAL)

```bash
# List all contexts
kubectl config get-contexts

# Show current context
kubectl config current-context

# Switch context
kubectl config use-context production-cluster

# Set default namespace for current context
kubectl config set-context --current --namespace=my-namespace

# ⚠️ ALWAYS verify before destructive operations
kubectl config current-context && kubectl config view --minify -o jsonpath='{.contexts[0].context.namespace}'
```

## Core Workflows

### Workflow: Safe Deploy

```bash
# 1. Verify you're targeting the right cluster and namespace
kubectl config current-context
kubectl get namespace my-namespace

# 2. Dry-run first — validates manifests without applying
kubectl apply -f deployment.yaml --dry-run=client -o yaml

# 3. Server-side dry-run (validates against cluster state)
kubectl apply -f deployment.yaml --dry-run=server

# 4. Apply
kubectl apply -f deployment.yaml -n my-namespace

# 5. Watch rollout
kubectl rollout status deployment/myapp -n my-namespace --timeout=5m

# 6. Verify pods are running
kubectl get pods -n my-namespace -l app=myapp
```

### Workflow: Rollback

```bash
# Check rollout history
kubectl rollout history deployment/myapp -n my-namespace

# Rollback to previous version
kubectl rollout undo deployment/myapp -n my-namespace

# Rollback to specific revision
kubectl rollout undo deployment/myapp -n my-namespace --to-revision=3

# Verify rollback
kubectl rollout status deployment/myapp -n my-namespace
```

### Workflow: Debugging Pods

```bash
# Get pod status
kubectl get pods -n my-namespace -o wide

# Describe pod (events, conditions, container status)
kubectl describe pod pod-name -n my-namespace

# View logs
kubectl logs pod-name -n my-namespace
kubectl logs pod-name -n my-namespace -c container-name  # Specific container
kubectl logs pod-name -n my-namespace --previous  # Previous crashed instance
kubectl logs -f pod-name -n my-namespace --tail=100  # Follow, last 100 lines

# Execute command in pod
kubectl exec pod-name -n my-namespace -- ls /app
kubectl exec -it pod-name -n my-namespace -- /bin/sh  # Interactive shell

# Port forward for local debugging
kubectl port-forward pod-name 8080:3000 -n my-namespace
kubectl port-forward svc/myapp 8080:80 -n my-namespace
```

### Workflow: Resource Inspection

```bash
# Get resources across all namespaces
kubectl get pods --all-namespaces
kubectl get pods -A  # Short form

# Get resources with labels
kubectl get pods -n my-namespace -l app=myapp,env=production

# Get resource YAML
kubectl get deployment myapp -n my-namespace -o yaml

# Get resource as JSON (for jq piping)
kubectl get pods -n my-namespace -o json | jq '.items[].metadata.name'

# Top (resource usage)
kubectl top pods -n my-namespace
kubectl top nodes

# Get events sorted by time
kubectl get events -n my-namespace --sort-by='.lastTimestamp'
```

### Workflow: Resource Management

```bash
# Scale
kubectl scale deployment myapp --replicas=3 -n my-namespace

# Delete pod (triggers restart via deployment)
kubectl delete pod pod-name -n my-namespace

# Delete all pods with a label
kubectl delete pods -l app=myapp -n my-namespace

# Force delete stuck pod
kubectl delete pod pod-name -n my-namespace --grace-period=0 --force

# Edit resource in-place (non-interactive alternative below)
kubectl patch deployment myapp -n my-namespace -p '{"spec":{"replicas":3}}'
```

## Flag Gotchas

### Namespace is NOT inherited from context by default in scripts

```bash
# ❌ DANGEROUS — applies to 'default' namespace if not set
kubectl apply -f deployment.yaml

# ✅ ALWAYS specify namespace explicitly
kubectl apply -f deployment.yaml -n my-namespace

# ✅ Or set namespace in the YAML itself
# metadata:
#   namespace: my-namespace
```

### `--dry-run=client` vs `--dry-run=server`

```bash
# client: validates YAML locally only (fast, no cluster needed)
kubectl apply -f deployment.yaml --dry-run=client -o yaml

# server: validates against actual cluster state (catches conflicts, quota, RBAC)
kubectl apply -f deployment.yaml --dry-run=server

# ✅ Use server-side for pre-deploy validation, client-side for syntax checking
```

### `delete` is immediate and irreversible

```bash
# ❌ DANGEROUS — no confirmation prompt
kubectl delete namespace production  # Deletes EVERYTHING in the namespace

# ✅ Use --dry-run first
kubectl delete namespace staging --dry-run=client

# ✅ For bulk deletes, list first
kubectl get pods -n staging -l app=old-version
# Review output, then delete
kubectl delete pods -n staging -l app=old-version
```

## Error Patterns

### `Error from server (Forbidden)` / RBAC denied

**Cause:** Your service account/user doesn't have permission.

**Fix:**
```bash
# Check your current auth
kubectl auth whoami  # k8s 1.27+
kubectl auth can-i get pods -n my-namespace

# Check what you CAN do
kubectl auth can-i --list -n my-namespace

# Common fix: check role binding
kubectl get rolebinding,clusterrolebinding -A | grep your-user
```

### `CrashLoopBackOff`

**Cause:** Container starts and immediately crashes, repeatedly.

**Fix:**
```bash
# Check logs from the crashed container
kubectl logs pod-name -n my-namespace --previous

# Check events
kubectl describe pod pod-name -n my-namespace | grep -A 20 Events

# Common causes: missing env vars, wrong command, OOM killed
kubectl get pod pod-name -n my-namespace -o jsonpath='{.status.containerStatuses[0].state}'
```

### `ImagePullBackOff`

**Cause:** Kubernetes can't pull the container image.

**Fix:**
```bash
# Check the exact error
kubectl describe pod pod-name -n my-namespace | grep -A 5 "Failed"

# Common causes:
# 1. Wrong image name/tag
# 2. Private registry without imagePullSecret
# 3. Image doesn't exist

# Verify image exists
docker pull your-registry/image:tag

# Check pull secrets
kubectl get secrets -n my-namespace | grep docker
```

### `Pending` pod stuck

**Cause:** Cluster can't schedule the pod (insufficient resources, node selector mismatch).

**Fix:**
```bash
# Check why it's pending
kubectl describe pod pod-name -n my-namespace | grep -A 10 Events

# Check node resources
kubectl top nodes
kubectl describe node node-name | grep -A 10 Allocatable
```

## Anti-Patterns

### Never `kubectl apply` without knowing your context

```bash
# ❌ DANGEROUS — could be any cluster
kubectl apply -f production-deployment.yaml

# ✅ Always verify first
kubectl config current-context
kubectl apply -f production-deployment.yaml -n production --dry-run=server
kubectl apply -f production-deployment.yaml -n production
```

### Never use `kubectl edit` in automation

```bash
# ❌ HANGS — opens editor
kubectl edit deployment myapp

# ✅ Use patch or apply instead
kubectl patch deployment myapp -p '{"spec":{"replicas":3}}'
kubectl apply -f updated-deployment.yaml
```

### Never delete a namespace without checking contents

```bash
# ❌ DESTROYS EVERYTHING — PVCs, secrets, deployments, all of it
kubectl delete namespace staging

# ✅ Inspect first
kubectl get all -n staging
kubectl get pvc -n staging
# Then delete if safe
```

## Composability

### kubectl + jq

```bash
# Get all container images in a namespace
kubectl get pods -n my-namespace -o json | \
  jq -r '.items[].spec.containers[].image' | sort -u

# Get pods not in Running state
kubectl get pods -n my-namespace -o json | \
  jq -r '.items[] | select(.status.phase != "Running") | .metadata.name'

# Get resource requests/limits
kubectl get pods -n my-namespace -o json | \
  jq '.items[].spec.containers[] | {name: .name, requests: .resources.requests, limits: .resources.limits}'
```

### kubectl + aws/gcloud

```bash
# EKS: Update kubeconfig and verify
aws eks update-kubeconfig --name my-cluster --region us-east-1
kubectl get nodes

# GKE: Switch clusters
gcloud container clusters get-credentials my-cluster --region us-central1
kubectl get nodes
```

## Agent Constraints

### Non-interactive operations

```bash
# ❌ HANGS — opens editor
kubectl edit deployment myapp

# ✅ Use patch for in-place changes
kubectl patch deployment myapp -n my-namespace \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"myapp","image":"myapp:v2"}]}}}}'

# ✅ Or apply from file
kubectl apply -f deployment.yaml -n my-namespace
```

### No pager for large outputs

```bash
# Pipe to cat if pager is suspected
kubectl get pods -A | cat
kubectl describe pod pod-name | cat

# Or use -o json for machine-parseable output
kubectl get pods -A -o json | jq '.items | length'
```

### Timeouts for wait operations

```bash
# Always set timeouts in automation
kubectl rollout status deployment/myapp --timeout=5m
kubectl wait --for=condition=ready pod -l app=myapp --timeout=120s
```

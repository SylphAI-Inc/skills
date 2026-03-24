---
name: terraform
description: "Terraform CLI — state management, import workflows, workspace migration, and safe apply patterns"
version: "1.6+"
category: iac
---

# Terraform CLI

> **Official docs:** https://developer.hashicorp.com/terraform/cli | **Reference:** https://developer.hashicorp.com/terraform/cli/commands

Terraform manages infrastructure as code. The CLI is powerful but has critical safety pitfalls around state management, import workflows, and destructive operations that require careful workflow discipline.

## Setup & Auth

```bash
# Installation (macOS)
brew install terraform

# Verify
terraform version

# Initialize a project (downloads providers, sets up backend)
terraform init

# Re-initialize after backend config changes
terraform init -reconfigure

# Upgrade providers to latest matching constraints
terraform init -upgrade
```

### Backend Authentication

Terraform inherits cloud provider auth. Ensure credentials are configured BEFORE running terraform commands:

```bash
# AWS — terraform uses the same auth as AWS CLI
aws sts get-caller-identity  # Verify you have valid credentials

# GCP
gcloud auth application-default login

# Azure
az login
```

## Core Workflows

### Workflow: Safe Apply (The Golden Path)

Always follow this sequence. Never skip steps.

```bash
# 1. Format code
terraform fmt -recursive

# 2. Validate syntax
terraform validate

# 3. Plan — ALWAYS review the plan
terraform plan -out=tfplan

# 4. Apply the EXACT plan you reviewed (not a new one)
terraform apply tfplan

# 5. Clean up plan file
rm tfplan
```

> ⚠️ `terraform apply` without `-out` generates a NEW plan at apply time — it may differ from what you reviewed.

### Workflow: Import Existing Resources

When you need to bring manually-created resources under Terraform management:

```bash
# 1. Write the resource block in your .tf file first
# (terraform import does NOT generate config)

# 2. Backup current state
terraform state pull > backup-$(date +%Y%m%d).tfstate

# 3. Import with state locking
terraform import -lock=true aws_s3_bucket.logs my-app-logs

# For resources inside modules:
terraform import -lock=true module.storage.aws_s3_bucket.logs my-app-logs

# 4. CRITICAL — Always plan after import to detect drift
terraform plan
# Review carefully: imported resources often have attributes
# your .tf file doesn't specify, causing unexpected changes on next apply

# 5. Iterate on your .tf config until plan shows "No changes"
```

### Workflow: Targeted Operations

When you need to apply/destroy specific resources only:

```bash
# Apply only one resource
terraform apply -target=aws_instance.web

# Destroy only one resource
terraform destroy -target=aws_instance.web

# ⚠️ Always run a full plan after targeted operations
terraform plan  # Ensure no unintended drift
```

### Workflow: State Inspection

```bash
# List all resources in state
terraform state list

# Show details of a specific resource
terraform state show aws_instance.web

# Pull full state as JSON (for scripting)
terraform state pull | jq '.resources[] | .type + "." + .name'
```

## Flag Gotchas

### `-auto-approve` skips ALL confirmation

```bash
# ❌ DANGEROUS in production — no human review
terraform apply -auto-approve

# ✅ Use plan files instead — you review the plan, then apply exactly that
terraform plan -out=tfplan
terraform apply tfplan
```

### `-refresh=false` uses stale state

```bash
# ❌ Can cause drift — state doesn't match reality
terraform plan -refresh=false

# ✅ Only use this when you KNOW state is fresh (e.g., just ran apply)
# Default behavior (refresh=true) is almost always what you want
```

### `-replace` vs `taint` (v1.5+)

```bash
# ❌ DEPRECATED — taint modifies state as a side effect
terraform taint aws_instance.web

# ✅ Use -replace flag instead (v1.5+) — no state modification until apply
terraform plan -replace=aws_instance.web
terraform apply -replace=aws_instance.web
```

## Error Patterns

### `Error: Error acquiring the state lock`

**Cause:** Another terraform process or a crashed process is holding the lock.

**Fix:**
```bash
# First, verify no other process is running
# Then force-unlock with the lock ID from the error message
terraform force-unlock LOCK_ID

# ⚠️ Only force-unlock if you're CERTAIN no other process is running
# Concurrent state modifications corrupt state
```

### `Error: Resource already exists`

**Cause:** You're trying to create a resource that already exists in the cloud but isn't in Terraform state.

**Fix:**
```bash
# Import it instead of creating
terraform import aws_s3_bucket.logs my-app-logs
terraform plan  # Verify alignment
```

### `Error: Provider produced inconsistent result after apply`

**Cause:** The cloud provider's API returned different values than expected. Common with eventual consistency (AWS).

**Fix:**
```bash
# Usually resolves by refreshing state
terraform refresh
terraform plan  # Verify clean
```

### `Error: Cycle` in resource dependencies

**Cause:** Two resources reference each other. Common with security groups.

**Fix:**
```bash
# Split the cycle using aws_security_group_rule (separate resource)
# instead of inline ingress/egress blocks in aws_security_group
```

## Anti-Patterns

### Never `terraform state rm` unless you intend to orphan the resource

```bash
# ❌ DANGEROUS — removes from state but resource still exists in cloud
# You'll lose Terraform management of this resource
terraform state rm aws_instance.web

# ✅ If you want to DELETE the resource:
terraform destroy -target=aws_instance.web

# ✅ If you want to MOVE/RENAME:
terraform state mv aws_instance.old aws_instance.new
```

### Never apply without a plan file in CI/CD

```bash
# ❌ CI/CD race condition — plan and apply may see different state
terraform plan    # Step 1 in pipeline
terraform apply -auto-approve  # Step 2 — NEW plan is generated!

# ✅ Lock the plan
terraform plan -out=tfplan
terraform apply tfplan  # Applies EXACTLY what was planned
```

### Never edit `.tfstate` files directly

```bash
# ❌ NEVER — corrupts state, breaks locking, causes data loss
vim terraform.tfstate

# ✅ Use state commands
terraform state mv ...
terraform state rm ...
terraform state pull > backup.tfstate  # For inspection only
```

## Composability

### Terraform + jq (state inspection)

```bash
# List all resource types in state
terraform state pull | jq -r '.resources[].type' | sort -u

# Find all AWS resources
terraform state pull | jq -r '.resources[] | select(.type | startswith("aws_")) | .type + "." + .name'

# Extract specific outputs
terraform output -json | jq -r '.vpc_id.value'
```

### Terraform + AWS CLI (drift detection)

```bash
# Compare Terraform state vs actual AWS state
INSTANCE_ID=$(terraform output -raw instance_id)
aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[].Instances[].State.Name' --output text
```

### Terraform + kubectl (EKS workflow)

```bash
# After terraform creates an EKS cluster
aws eks update-kubeconfig --name $(terraform output -raw cluster_name) --region us-east-1
kubectl get nodes  # Verify cluster access
```

## Agent Constraints

### Non-interactive apply

```bash
# ❌ HANGS — terraform apply prompts for "yes"
terraform apply

# ✅ Use plan file (preferred — no prompt needed)
terraform plan -out=tfplan
terraform apply tfplan

# ✅ Or auto-approve (use only in CI/CD with prior plan review)
terraform apply -auto-approve
```

### No pager for large outputs

```bash
# Terraform doesn't use a pager, but piped tools might
terraform state list  # Safe — no pager
terraform state pull | cat  # Force no-pager for downstream
```

### Lock management in automation

```bash
# Always use -lock-timeout in CI/CD to handle transient lock conflicts
terraform plan -lock-timeout=5m -out=tfplan
terraform apply -lock-timeout=5m tfplan
```

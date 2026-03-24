---
name: azure-cli
description: "Azure CLI — resource groups, AKS, App Service, subscription management, and query patterns"
version: "2.60+"
category: cloud
---

# Azure CLI (az)

> **Official docs:** https://learn.microsoft.com/en-us/cli/azure/ | **Reference:** https://learn.microsoft.com/en-us/cli/azure/reference-index

The Azure CLI manages Azure resources. Key challenges include subscription switching (operating on wrong subscription), resource group scoping, and the JMESPath `--query` syntax shared with AWS but with subtle differences.

## Setup & Auth

```bash
# Installation (macOS)
brew install azure-cli

# Installation (Linux)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Verify
az version

# Login (interactive — opens browser)
az login

# Login with service principal (CI/CD)
az login --service-principal \
  --username $APP_ID \
  --password $CLIENT_SECRET \
  --tenant $TENANT_ID

# Login with managed identity (Azure VMs/containers)
az login --identity

# Check current account
az account show
```

### Subscription Management

```bash
# List all subscriptions
az account list --output table

# Set default subscription
az account set --subscription "My Subscription Name"
# Or by ID:
az account set --subscription xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Verify current subscription
az account show --query "{name:name, id:id, state:state}" --output table

# ⚠️ ALWAYS verify subscription before destructive operations
az account show --query name --output tsv
```

## Core Workflows

### Workflow: Resource Groups

```bash
# List resource groups
az group list --output table

# Create resource group
az group create --name my-rg --location eastus

# Delete resource group (deletes ALL resources inside)
az group delete --name my-rg --yes --no-wait

# List resources in a group
az resource list --resource-group my-rg --output table
```

### Workflow: AKS (Kubernetes)

```bash
# Create cluster
az aks create \
  --resource-group my-rg \
  --name my-cluster \
  --node-count 3 \
  --node-vm-size Standard_DS2_v2 \
  --generate-ssh-keys

# Get credentials (configures kubectl)
az aks get-credentials --resource-group my-rg --name my-cluster

# List clusters
az aks list --output table

# Scale
az aks scale --resource-group my-rg --name my-cluster --node-count 5

# Upgrade
az aks get-upgrades --resource-group my-rg --name my-cluster --output table
az aks upgrade --resource-group my-rg --name my-cluster --kubernetes-version 1.28.0

# Delete
az aks delete --resource-group my-rg --name my-cluster --yes --no-wait
```

### Workflow: App Service (Web Apps)

```bash
# Create app service plan
az appservice plan create \
  --name my-plan \
  --resource-group my-rg \
  --sku B1 \
  --is-linux

# Create web app
az webapp create \
  --resource-group my-rg \
  --plan my-plan \
  --name my-webapp \
  --runtime "PYTHON:3.12"

# Deploy from local code
az webapp up --name my-webapp --resource-group my-rg --runtime "PYTHON:3.12"

# Set environment variables
az webapp config appsettings set \
  --resource-group my-rg \
  --name my-webapp \
  --settings DB_URL=postgres://... SECRET_KEY=xxx

# View logs
az webapp log tail --resource-group my-rg --name my-webapp

# Restart
az webapp restart --resource-group my-rg --name my-webapp
```

### Workflow: Storage Accounts

```bash
# Create storage account
az storage account create \
  --name mystorageaccount \
  --resource-group my-rg \
  --location eastus \
  --sku Standard_LRS

# Create container (blob)
az storage container create --name mycontainer --account-name mystorageaccount

# Upload blob
az storage blob upload \
  --account-name mystorageaccount \
  --container-name mycontainer \
  --name remote-name.txt \
  --file local-file.txt

# List blobs
az storage blob list --account-name mystorageaccount --container-name mycontainer --output table

# Download
az storage blob download \
  --account-name mystorageaccount \
  --container-name mycontainer \
  --name remote-name.txt \
  --file local-file.txt

# Generate SAS token
az storage blob generate-sas \
  --account-name mystorageaccount \
  --container-name mycontainer \
  --name file.txt \
  --permissions r \
  --expiry 2025-12-31T00:00:00Z
```

## Flag Gotchas

### `--query` uses JMESPath (same as AWS)

```bash
# ❌ WRONG — jq syntax
az vm list --query '.[]|.name'

# ✅ CORRECT — JMESPath (no leading dot)
az vm list --query "[].name" --output tsv

# ✅ Filter and select
az vm list --query "[?powerState=='VM running'].[name,resourceGroup]" --output table

# ✅ Named columns
az vm list --query "[].{Name:name, RG:resourceGroup, Status:powerState}" --output table
```

### `--output` types

```bash
# table: human-readable (default for most commands)
az vm list --output table

# json: for jq piping
az vm list --output json | jq '.[].name'

# tsv: tab-separated (best for scripting)
az vm list --query "[].name" --output tsv

# yaml: for inspection
az vm list --output yaml
```

### `--yes` / `-y` and `--no-wait`

```bash
# ❌ HANGS — asks for confirmation
az group delete --name my-rg

# ✅ Auto-confirm
az group delete --name my-rg --yes

# ✅ Don't wait for completion (async)
az group delete --name my-rg --yes --no-wait
```

## Error Patterns

### `The subscription 'xxx' could not be found`

**Cause:** Wrong subscription set or not logged into right tenant.

**Fix:**
```bash
az account list --output table
az account set --subscription "correct-subscription"
```

### `AuthorizationFailed` / `does not have authorization to perform action`

**Cause:** Insufficient RBAC permissions.

**Fix:**
```bash
# Check current identity
az account show
az ad signed-in-user show

# Check role assignments
az role assignment list --assignee $(az account show --query user.name -o tsv) --output table
```

### `ResourceGroupNotFound`

**Cause:** Resource group doesn't exist or wrong subscription is active.

**Fix:**
```bash
# Verify subscription
az account show --query name -o tsv

# List resource groups
az group list --output table

# Check if resource group exists
az group exists --name my-rg
```

### `Conflict` / `OperationNotAllowed`

**Cause:** Resource in a state that doesn't allow the operation (e.g., deleting a running VM).

**Fix:**
```bash
# Check resource state
az vm show --resource-group my-rg --name my-vm --query powerState -o tsv

# Deallocate first, then delete
az vm deallocate --resource-group my-rg --name my-vm
az vm delete --resource-group my-rg --name my-vm --yes
```

## Anti-Patterns

### Never forget to set subscription

```bash
# ❌ DANGEROUS — may operate on wrong subscription
az vm delete --resource-group my-rg --name my-vm --yes

# ✅ Verify subscription first
az account show --query "{name:name, id:id}" -o table
az vm delete --resource-group my-rg --name my-vm --yes
```

### Never skip resource group scoping

```bash
# ❌ SLOW and CONFUSING — lists across all resource groups
az resource list

# ✅ Always scope to resource group
az resource list --resource-group my-rg --output table
```

## Composability

### az + jq

```bash
# Get all running VMs with their IPs
az vm list-ip-addresses --output json | \
  jq -r '.[] | [.virtualMachine.name, .virtualMachine.network.publicIpAddresses[0].ipAddress] | @tsv'

# Get all app service URLs
az webapp list --query "[].{name:name, url:defaultHostName}" --output json | \
  jq -r '.[] | "\(.name): https://\(.url)"'
```

### az + kubectl

```bash
# Switch to AKS cluster
az aks get-credentials --resource-group my-rg --name my-cluster
kubectl config current-context
kubectl get nodes
```

### az + terraform

```bash
# Set up Azure auth for Terraform
az login
export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
export ARM_TENANT_ID=$(az account show --query tenantId -o tsv)
terraform plan
```

## Agent Constraints

### Non-interactive operations

```bash
# ❌ HANGS — opens browser for login
az login

# ✅ Service principal login (CI/CD)
az login --service-principal -u $APP_ID -p $SECRET --tenant $TENANT_ID

# ❌ HANGS — confirmation prompts
az group delete --name my-rg

# ✅ Auto-confirm with --yes
az group delete --name my-rg --yes --no-wait

# ✅ Disable prompts globally
az config set core.no_color=true
az config set core.only_show_errors=true
```

### Output for parsing

```bash
# Always use --output tsv or --output json for scripting
VM_NAME=$(az vm list --query "[0].name" --output tsv)

# Combine --query + --output tsv for single values
SUBSCRIPTION=$(az account show --query id --output tsv)
```

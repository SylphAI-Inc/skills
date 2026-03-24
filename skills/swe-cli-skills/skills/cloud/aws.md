---
name: aws-cli
description: "AWS CLI v2 — IAM auth, S3 operations, EC2 queries, Lambda management, JMESPath filtering, and cross-service workflows"
version: "2.x"
category: cloud
---

# AWS CLI v2

> **Official docs:** https://docs.aws.amazon.com/cli/latest/userguide/ | **Reference:** https://awscli.amazonaws.com/v2/documentation/api/latest/index.html

The AWS CLI is the primary interface for managing AWS services. It's one of the most complex CLIs in the SWE toolbox — with 200+ services, non-obvious filter ordering, and powerful but tricky JMESPath queries.

## Setup & Auth

```bash
# Installation (macOS)
brew install awscli

# Installation (Linux)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Verify
aws --version
```

### Auth Methods (in order of preference)

```bash
# Method 1: SSO (recommended for organizations)
aws configure sso
aws sso login --profile my-profile

# Method 2: Environment variables (CI/CD)
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1

# Method 3: Named profiles
aws configure --profile production
# Then use: aws s3 ls --profile production

# Verify current identity
aws sts get-caller-identity
```

### Profile Management

```bash
# List configured profiles
aws configure list-profiles

# Check which profile is active
aws configure list

# Use a specific profile for one command
aws s3 ls --profile staging

# Set default profile for session
export AWS_PROFILE=staging
```

## Core Workflows

### Workflow: S3 File Operations

```bash
# List buckets
aws s3 ls

# List objects in a bucket (with human-readable sizes)
aws s3 ls s3://my-bucket/ --recursive --human-readable --summarize

# Upload a file
aws s3 cp local-file.txt s3://my-bucket/path/

# Upload a directory
aws s3 cp ./local-dir s3://my-bucket/path/ --recursive

# Sync (only uploads changed files)
aws s3 sync ./local-dir s3://my-bucket/path/

# Download
aws s3 cp s3://my-bucket/path/file.txt ./local-file.txt

# Delete
aws s3 rm s3://my-bucket/path/file.txt
aws s3 rm s3://my-bucket/path/ --recursive  # Delete directory
```

### Workflow: EC2 Instance Management

```bash
# List running instances with useful columns
aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" \
  --query 'Reservations[].Instances[].[InstanceId,InstanceType,PrivateIpAddress,Tags[?Key==`Name`].Value|[0]]' \
  --output table

# Start/Stop instances
aws ec2 start-instances --instance-ids i-1234567890abcdef0
aws ec2 stop-instances --instance-ids i-1234567890abcdef0

# Get console output (debugging boot issues)
aws ec2 get-console-output --instance-id i-1234567890abcdef0 --output text
```

### Workflow: Lambda Functions

```bash
# List functions
aws lambda list-functions --query 'Functions[].[FunctionName,Runtime,MemorySize]' --output table

# Invoke a function
aws lambda invoke --function-name my-function --payload '{"key":"value"}' output.json

# View recent logs
aws logs tail /aws/lambda/my-function --since 1h --follow

# Update function code from zip
zip -r function.zip . && aws lambda update-function-code \
  --function-name my-function --zip-file fileb://function.zip
```

### Workflow: CloudWatch Logs

```bash
# Tail logs in real-time
aws logs tail /aws/lambda/my-function --follow --since 10m

# Search logs with filter pattern
aws logs filter-log-events \
  --log-group-name /aws/lambda/my-function \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000

# List log groups
aws logs describe-log-groups --query 'logGroups[].[logGroupName]' --output text
```

## Flag Gotchas

### S3 `--exclude` / `--include` ordering (CRITICAL)

AWS applies filters **left-to-right**. Order matters.

```bash
# ❌ WRONG — includes NOTHING because exclude overrides at the end
aws s3 sync . s3://bucket --include "*.json" --exclude "*"

# ✅ CORRECT — exclude everything first, then include what you want
aws s3 sync . s3://bucket --exclude "*" --include "*.json"

# ✅ Multiple includes work too
aws s3 sync . s3://bucket --exclude "*" --include "*.json" --include "*.yaml"

# ✅ Dry run first to verify
aws s3 sync . s3://bucket --exclude "*" --include "*.json" --dryrun
```

### `--query` uses JMESPath, not jq syntax

```bash
# ❌ WRONG — this is jq syntax, not JMESPath
aws ec2 describe-instances --query '.Reservations[].Instances[]'

# ✅ CORRECT — JMESPath has no leading dot
aws ec2 describe-instances --query 'Reservations[].Instances[]'

# ✅ Flatten nested arrays with []
aws ec2 describe-instances --query 'Reservations[].Instances[].InstanceId'

# ✅ Filter with ?
aws ec2 describe-instances --query 'Reservations[].Instances[?State.Name==`running`].InstanceId'

# ✅ Select specific fields (use [] for flat arrays, {} for objects)
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].[InstanceId, State.Name]' \
  --output table
```

### `--output` affects what `--query` returns

```bash
# text output: one value per line (great for scripting)
aws ec2 describe-instances --query 'Reservations[].Instances[].InstanceId' --output text

# table output: formatted table (great for human review)
aws ec2 describe-instances --query 'Reservations[].Instances[].[InstanceId,State.Name]' --output table

# json output: raw JSON (great for piping to jq)
aws ec2 describe-instances --output json | jq '.Reservations[].Instances[].InstanceId'
```

## Error Patterns

### `An error occurred (AccessDenied)`

**Cause:** IAM permissions insufficient for this operation.

**Fix:**
```bash
# Check who you are
aws sts get-caller-identity

# Check if you're using the right profile
aws configure list

# Common issue: assumed role expired
aws sts get-session-token  # If this fails, re-authenticate
```

### `Unable to locate credentials`

**Cause:** No auth configured — no env vars, no config file, no instance role.

**Fix:**
```bash
# Check for credentials
aws configure list
# If empty, configure:
aws configure
# Or set environment variables (see Setup section)
```

### `ExpiredTokenException`

**Cause:** SSO or session token expired.

**Fix:**
```bash
# SSO
aws sso login --profile my-profile

# STS session
aws sts get-session-token --duration-seconds 3600
```

### `InvalidParameterValue` / `ValidationError` on filters

**Cause:** Wrong filter syntax — `Name` and `Values` are case-sensitive.

**Fix:**
```bash
# ❌ WRONG — lowercase 'name' and 'values'
aws ec2 describe-instances --filters "name=instance-state-name,values=running"

# ✅ CORRECT — capitalized 'Name' and 'Values'
aws ec2 describe-instances --filters "Name=instance-state-name,Values=running"
```

## Anti-Patterns

### Never hardcode credentials in commands or scripts

```bash
# ❌ NEVER — credentials in command history
aws configure set aws_access_key_id AKIA... --profile prod

# ✅ Use environment variables or SSO
export AWS_PROFILE=prod
aws sso login
```

### Never use `--recursive` delete without verification

```bash
# ❌ DANGEROUS — no confirmation, immediate delete
aws s3 rm s3://production-bucket/ --recursive

# ✅ List first, then delete
aws s3 ls s3://production-bucket/ --recursive --summarize
# Review output, then:
aws s3 rm s3://production-bucket/specific-path/ --recursive --dryrun
# Review dryrun, then:
aws s3 rm s3://production-bucket/specific-path/ --recursive
```

### Never ignore pagination

```bash
# ❌ WRONG — only returns first page (default ~100 items)
aws s3api list-objects-v2 --bucket my-bucket

# ✅ CORRECT — use --no-paginate or handle pagination
aws s3api list-objects-v2 --bucket my-bucket --no-paginate

# ✅ Or pipe through CLI's built-in pagination
aws s3api list-objects-v2 --bucket my-bucket --query 'Contents[].Key' --output text
```

## Composability

### AWS + jq (JSON processing)

```bash
# Get instance IDs for a specific tag
aws ec2 describe-instances \
  --filters "Name=tag:Environment,Values=production" \
  --output json | jq -r '.Reservations[].Instances[].InstanceId'

# Get Lambda function sizes, sorted
aws lambda list-functions --output json | \
  jq -r '.Functions[] | [.FunctionName, .CodeSize] | @tsv' | sort -t$'\t' -k2 -n -r
```

### AWS + xargs (batch operations)

```bash
# Stop all instances with a tag
aws ec2 describe-instances \
  --filters "Name=tag:Environment,Values=dev" "Name=instance-state-name,Values=running" \
  --query 'Reservations[].Instances[].InstanceId' --output text | \
  xargs -n1 aws ec2 stop-instances --instance-ids

# Delete all objects in a path (faster than rm --recursive for huge buckets)
aws s3api list-objects-v2 --bucket my-bucket --prefix old-data/ \
  --query 'Contents[].Key' --output text | \
  tr '\t' '\n' | xargs -P4 -I{} aws s3api delete-object --bucket my-bucket --key {}
```

### AWS + terraform

```bash
# Verify terraform-managed resources match AWS
INSTANCE_ID=$(terraform output -raw instance_id)
aws ec2 describe-instances --instance-ids $INSTANCE_ID \
  --query 'Reservations[].Instances[].State.Name' --output text
```

## Agent Constraints

### No pager

```bash
# ❌ HANGS — AWS CLI uses a pager for long output
aws ec2 describe-instances

# ✅ Disable pager globally for this session
export AWS_PAGER=""

# ✅ Or per-command
aws ec2 describe-instances --no-cli-pager

# ✅ Or pipe to cat
aws ec2 describe-instances | cat
```

### Non-interactive auth

```bash
# ❌ HANGS — aws configure prompts for input
aws configure

# ✅ Use environment variables instead
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1

# ✅ Or set individual values non-interactively
aws configure set region us-east-1 --profile myprofile
aws configure set output json --profile myprofile
```

### Waiter pattern (for async operations)

```bash
# ❌ WRONG — instance isn't ready immediately after start
aws ec2 start-instances --instance-ids i-1234567890abcdef0
aws ec2 describe-instances --instance-ids i-1234567890abcdef0  # May show 'pending'

# ✅ Use built-in waiters
aws ec2 start-instances --instance-ids i-1234567890abcdef0
aws ec2 wait instance-running --instance-ids i-1234567890abcdef0
# Command returns only when instance is fully running
```

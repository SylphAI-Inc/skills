# flyctl — Fly.io CLI

## Setup & Auth

```bash
# Install
brew install flyctl            # macOS
curl -L https://fly.io/install.sh | sh  # Linux

# Login (opens browser)
fly auth login

# Login with token (CI/CD)
export FLY_API_TOKEN=xxx
fly auth token  # verify

# Check current user
fly auth whoami
```

## App Management

```bash
# Create a new app
fly apps create my-app

# Create in specific region
fly apps create my-app --machines

# List apps
fly apps list

# Destroy app (irreversible)
fly apps destroy my-app

# App status
fly status
fly status -a my-app
```

## Deployments

```bash
# Deploy (builds and deploys)
fly deploy

# Deploy specific Dockerfile
fly deploy --dockerfile Dockerfile.prod

# Deploy pre-built image
fly deploy --image registry/myapp:v1.2.3

# Deploy without building (remote builder)
fly deploy --remote-only

# Deploy with build args
fly deploy --build-arg NODE_ENV=production

# Deploy to specific app
fly deploy -a my-app

# Deploy and wait for health checks
fly deploy --wait-timeout 300

# Rollback to previous release
fly releases list
fly deploy --image <previous-image-ref>
```

## Scaling

```bash
# Scale machine count
fly scale count 3

# Scale machine count per region
fly scale count 2 --region ord
fly scale count 1 --region lhr

# Scale machine size
fly scale vm shared-cpu-1x
fly scale vm shared-cpu-2x --memory 512
fly scale vm performance-1x

# Show current scale
fly scale show

# Auto-scale (min/max machines)
fly autoscale set min=1 max=10
```

### Machine Sizes

| Size | CPU | RAM | Use |
|------|-----|-----|-----|
| `shared-cpu-1x` | shared | 256MB | Dev, small apps |
| `shared-cpu-2x` | shared | 512MB | Medium traffic |
| `shared-cpu-4x` | shared | 1GB | Higher traffic |
| `performance-1x` | 1 dedicated | 2GB | Production |
| `performance-2x` | 2 dedicated | 4GB | Heavy workloads |

## Secrets

```bash
# Set a secret
fly secrets set DATABASE_URL="postgres://..."

# Set multiple secrets
fly secrets set SECRET1=val1 SECRET2=val2

# Set from file
fly secrets set MY_CERT=- < cert.pem

# List secrets (names only, not values)
fly secrets list

# Unset a secret
fly secrets unset DATABASE_URL
```

> **⚠️ Setting secrets triggers a redeploy.** Set multiple secrets in one command to avoid multiple redeploys.

## Regions

```bash
# List available regions
fly platform regions

# Add region
fly regions add ord lhr

# Remove region
fly regions remove lhr

# List app regions
fly regions list

# Set primary region
fly regions set ord
```

## Volumes (Persistent Storage)

```bash
# Create a volume
fly volumes create mydata --region ord --size 10

# List volumes
fly volumes list

# Extend volume
fly volumes extend vol_xxx --size 20

# Destroy volume
fly volumes destroy vol_xxx

# Snapshot a volume
fly volumes snapshots list vol_xxx
```

## Networking

```bash
# Allocate IPv4
fly ips allocate-v4

# Allocate IPv6
fly ips allocate-v6

# List IPs
fly ips list

# Release IP
fly ips release <ip-address>

# Set up WireGuard tunnel
fly wireguard create

# Proxy to app (local port forwarding)
fly proxy 5432:5432 -a my-db-app
```

## Databases (Fly Postgres)

```bash
# Create Postgres cluster
fly postgres create --name my-db

# Attach database to app
fly postgres attach my-db -a my-app

# Connect via psql
fly postgres connect -a my-db

# Proxy Postgres locally
fly proxy 5432 -a my-db
# Then: psql postgres://localhost:5432

# List database clusters
fly postgres list
```

## Logs & Monitoring

```bash
# Stream logs
fly logs

# Stream logs for specific app
fly logs -a my-app

# Filter by region
fly logs --region ord

# Check app status
fly status

# Machine status
fly machine list
fly machine status <machine-id>

# SSH into a machine
fly ssh console
fly ssh console -a my-app

# Run one-off command
fly ssh console -C "ls -la /app"
```

## Common Patterns

### Blue-Green Deploys

```bash
# Deploy canary
fly deploy --strategy canary

# Promote or rollback based on metrics
fly deploy --strategy rolling
```

### Multi-Region Postgres

```bash
# Create primary
fly postgres create --name my-db --region ord

# Add read replica
fly postgres create --name my-db-replica --region lhr \
  --initial-cluster-size 1 --flex
```

### CI/CD (GitHub Actions)

```yaml
- name: Deploy to Fly.io
  uses: superfly/flyctl-actions/setup-flyctl@master
- run: flyctl deploy --remote-only
  env:
    FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

## Gotchas

1. **Secrets trigger redeploy** — Each `fly secrets set` call redeploys. Set all secrets in one command: `fly secrets set A=1 B=2 C=3`.
2. **Volumes are region-locked** — A volume in `ord` can only be attached to machines in `ord`. Plan regions before creating volumes.
3. **Shared CPU = burstable** — `shared-cpu-*` machines can be throttled under sustained load. Use `performance-*` for production.
4. **`fly deploy` builds remotely by default** — This can be slow. Use `--local-only` for local Docker builds, or `--image` for pre-built images.
5. **No `fly restart`** — Use `fly apps restart` or `fly machine restart <id>`. Common source of confusion.
6. **IPv4 costs money** — Dedicated IPv4 addresses cost $2/mo. IPv6 is free. Use shared IPv4 when possible.
7. **`fly proxy` is for development** — Don't use it in production. It tunnels through WireGuard and adds latency.
8. **Health checks are critical** — If health checks fail, deploy is rolled back. Configure them properly in `fly.toml`.

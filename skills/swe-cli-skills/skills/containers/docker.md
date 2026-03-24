---
name: docker
description: "Docker CLI — build cache optimization, multi-stage builds, compose v2, cleanup, and debugging"
version: "24.x+ / Compose v2"
category: containers
---

# Docker CLI

> **Official docs:** https://docs.docker.com/reference/cli/docker/ | **Compose:** https://docs.docker.com/compose/reference/

Docker builds, ships, and runs containers. The CLI is deceptively simple — but build cache busting, dangling images, compose version confusion, and cleanup are constant pain points.

## Setup & Auth

```bash
# Verify installation
docker version
docker compose version  # v2 (plugin), NOT docker-compose (v1)

# Login to a registry
docker login
docker login ghcr.io
docker login <account-id>.dkr.ecr.<region>.amazonaws.com  # AWS ECR

# AWS ECR auth (expires every 12h)
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
```

## Core Workflows

### Workflow: Build & Run

```bash
# Build an image
docker build -t myapp:latest .

# Build with a specific Dockerfile
docker build -t myapp:latest -f Dockerfile.prod .

# Run a container
docker run -d --name myapp -p 8080:3000 myapp:latest

# Run with environment variables
docker run -d --name myapp -p 8080:3000 \
  -e DATABASE_URL=postgres://... \
  -e NODE_ENV=production \
  myapp:latest

# Run interactively (for debugging)
docker run -it --rm myapp:latest /bin/sh
```

### Workflow: Build Cache Optimization

```bash
# ✅ CORRECT Dockerfile pattern — dependencies first, source code last
# This maximizes cache hits when only source code changes

# Example for Python:
# COPY requirements.txt .         ← changes rarely
# RUN pip install -r requirements.txt  ← cached if requirements unchanged
# COPY . .                        ← changes frequently (only this layer rebuilds)

# Example for Node.js:
# COPY package.json package-lock.json ./
# RUN npm ci
# COPY . .

# Force a clean build (no cache)
docker build --no-cache -t myapp:latest .

# Build with specific target stage
docker build --target builder -t myapp:builder .
```

### Workflow: Docker Compose

```bash
# Start all services (detached)
docker compose up -d

# Start with rebuild
docker compose up -d --build

# View logs
docker compose logs -f
docker compose logs -f service-name

# Stop all services
docker compose down

# Stop and remove volumes (⚠️ destroys data)
docker compose down -v

# Run a one-off command in a service
docker compose exec web bash
docker compose run --rm web python manage.py migrate
```

### Workflow: Debugging

```bash
# Shell into a running container
docker exec -it container-name /bin/sh
# or /bin/bash if available

# View logs
docker logs container-name
docker logs -f container-name --tail 100  # Follow, last 100 lines

# Inspect container details
docker inspect container-name

# Check resource usage
docker stats

# View container processes
docker top container-name

# Copy files from container
docker cp container-name:/app/file.txt ./local-file.txt
```

### Workflow: Cleanup

```bash
# Remove stopped containers
docker container prune -f

# Remove unused images
docker image prune -f        # Only dangling
docker image prune -a -f     # ALL unused images

# Remove unused volumes (⚠️ may lose data)
docker volume prune -f

# Nuclear cleanup — everything unused
docker system prune -af --volumes

# Check disk usage
docker system df
```

## Flag Gotchas

### `docker compose` vs `docker-compose` (v1 vs v2)

```bash
# ❌ DEPRECATED — v1 standalone binary (may not be installed)
docker-compose up -d

# ✅ CORRECT — v2 is a Docker plugin
docker compose up -d

# Key v2 differences:
# - Container names use '-' not '_': myapp-web-1 (not myapp_web_1)
# - Build is parallel by default
# - profiles support for conditional service startup
```

### `docker run` vs `docker exec`

```bash
# ❌ WRONG — creates a NEW container from the image
docker run -it myapp bash  # New container, not the running one!

# ✅ CORRECT — enters the RUNNING container
docker exec -it myapp bash  # Attaches to existing container

# Check what's running first
docker ps
```

### `COPY` vs `ADD` in Dockerfiles

```bash
# ❌ AVOID — ADD has hidden behavior (auto-extracts tars, fetches URLs)
ADD app.tar.gz /app/

# ✅ PREFER — COPY is explicit and predictable
COPY app.tar.gz /app/
RUN tar -xzf /app/app.tar.gz

# Only use ADD when you WANT auto-extraction:
ADD https://example.com/file.tar.gz /tmp/
```

## Error Patterns

### `no space left on device`

**Cause:** Docker's storage driver filled up the disk with images, containers, and volumes.

**Fix:**
```bash
# Check what's using space
docker system df

# Clean up (safe — only removes unused)
docker system prune -af
docker volume prune -f

# Nuclear option if still full
docker system prune -af --volumes
```

### `port is already allocated`

**Cause:** Another container or process is using the port.

**Fix:**
```bash
# Find what's using the port
lsof -i :8080  # macOS/Linux
docker ps --filter "publish=8080"

# Stop the conflicting container
docker stop conflicting-container

# Or use a different port
docker run -p 8081:3000 myapp
```

### `COPY failed: file not found`

**Cause:** File path is relative to the build context, not the Dockerfile location. Or `.dockerignore` is excluding it.

**Fix:**
```bash
# Check build context
ls -la  # From where you run docker build

# Check .dockerignore
cat .dockerignore  # Is your file excluded?

# Build with explicit context
docker build -t myapp -f docker/Dockerfile .  # Context is still '.'
```

### `exec format error` (M1/ARM)

**Cause:** Image built for different architecture (amd64 image on ARM Mac).

**Fix:**
```bash
# Build for specific platform
docker build --platform linux/amd64 -t myapp .

# Build multi-arch
docker buildx build --platform linux/amd64,linux/arm64 -t myapp .

# Run with platform emulation
docker run --platform linux/amd64 myapp
```

## Anti-Patterns

### Never use `latest` tag in production

```bash
# ❌ UNPREDICTABLE — `latest` changes with every push
docker pull myapp:latest

# ✅ Pin to a specific version or SHA
docker pull myapp:1.2.3
docker pull myapp@sha256:abc123...
```

### Never run containers as root without reason

```bash
# ❌ Security risk — container has root access
# (default if no USER specified)

# ✅ Add a non-root user in Dockerfile
# RUN addgroup -S app && adduser -S app -G app
# USER app
```

### Never store secrets in images

```bash
# ❌ LEAKED — secrets baked into image layer
# ENV DATABASE_PASSWORD=secret123

# ✅ Pass at runtime
docker run -e DATABASE_PASSWORD=secret123 myapp
# Or use Docker secrets / .env file
docker compose --env-file .env up
```

## Composability

### Docker + jq (inspect containers)

```bash
# Get container IP addresses
docker inspect myapp | jq -r '.[0].NetworkSettings.IPAddress'

# Get all environment variables
docker inspect myapp | jq '.[0].Config.Env'

# Get port mappings
docker inspect myapp | jq '.[0].NetworkSettings.Ports'
```

### Docker + AWS ECR

```bash
# Full ECR workflow
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_REGISTRY
docker build -t $ECR_REGISTRY/myapp:$GIT_SHA .
docker push $ECR_REGISTRY/myapp:$GIT_SHA
```

## Agent Constraints

### Non-interactive container access

```bash
# ❌ HANGS — opens interactive shell
docker run -it myapp bash

# ✅ Run a specific command and exit
docker run --rm myapp cat /etc/os-release
docker exec myapp ls /app

# ✅ For debugging, use non-interactive inspection
docker logs myapp --tail 50
docker inspect myapp
```

### Build output in CI/CD

```bash
# Reduce noisy output
docker build -q -t myapp .  # Quiet mode — only outputs image ID

# Progress type for CI
docker build --progress=plain -t myapp .  # Readable logs in CI
```

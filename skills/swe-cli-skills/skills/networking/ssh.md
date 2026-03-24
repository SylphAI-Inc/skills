---
name: ssh
description: "SSH/SCP — tunneling, ProxyJump, key management, port forwarding, and agent-safe alternatives"
version: "OpenSSH 9.x"
category: networking
---

# SSH / SCP

> **Official docs:** https://www.openssh.com/manual.html | **Reference:** https://man.openbsd.org/ssh

SSH is the standard for remote server access and secure file transfer. For AI agents, the critical challenges are interactive password prompts (hang), tunnel direction confusion, and bastion/jump host patterns.

## Setup & Auth

```bash
# Verify
ssh -V

# Generate key pair
ssh-keygen -t ed25519 -C "your@email.com" -f ~/.ssh/id_ed25519 -N ""
# -N "" sets empty passphrase (non-interactive)

# Copy public key to remote server (interactive — tell user to do this)
ssh-copy-id user@remote-server

# Test connection
ssh -o ConnectTimeout=5 -o BatchMode=yes user@remote-server echo "connected"
```

### SSH Config File (~/.ssh/config)

```bash
# ✅ Use config file for complex setups — avoids long command lines
# ~/.ssh/config example:

# Host production
#     HostName 10.0.1.50
#     User deploy
#     IdentityFile ~/.ssh/production_key
#     ProxyJump bastion
#
# Host bastion
#     HostName bastion.example.com
#     User admin
#     IdentityFile ~/.ssh/bastion_key

# Then simply:
ssh production  # Uses all config automatically
```

## Core Workflows

### Workflow: Remote Command Execution

```bash
# Run a single command remotely
ssh user@server 'ls -la /var/log'

# Run multiple commands
ssh user@server 'cd /app && git pull && sudo systemctl restart app'

# Run with environment variable
ssh user@server "DEPLOY_ENV=production ./deploy.sh"

# Run script from local machine on remote
ssh user@server 'bash -s' < local-script.sh

# Run with sudo (non-interactive, requires NOPASSWD in sudoers)
ssh user@server 'sudo systemctl restart nginx'
```

### Workflow: File Transfer (SCP)

```bash
# Copy file to remote
scp local-file.txt user@server:/remote/path/

# Copy file from remote
scp user@server:/remote/path/file.txt ./local-file.txt

# Copy directory recursively
scp -r ./local-dir user@server:/remote/path/

# Copy through bastion/jump host
scp -o ProxyJump=user@bastion local-file.txt user@target:/path/

# ✅ Better alternative: rsync over ssh (resumes, shows progress)
rsync -avz -e ssh ./local-dir user@server:/remote/path/
```

### Workflow: Port Forwarding / Tunnels

```bash
# LOCAL FORWARD — access remote service on localhost
# "I want to access remote-db:5432 on my localhost:5432"
ssh -L 5432:remote-db:5432 user@bastion -N
# Now: psql -h localhost -p 5432

# REMOTE FORWARD — expose local service to remote
# "I want the remote server to access my localhost:3000"
ssh -R 8080:localhost:3000 user@server -N
# Now on server: curl http://localhost:8080

# DYNAMIC FORWARD (SOCKS proxy)
ssh -D 1080 user@server -N
# Configure browser/tools to use SOCKS5 proxy at localhost:1080

# -N = no remote command (tunnel only)
# -f = background the tunnel (NOT agent-safe — use & instead)
```

### Workflow: Jump/Bastion Hosts

```bash
# Direct jump (OpenSSH 7.3+)
ssh -J user@bastion user@internal-server

# Multiple jumps
ssh -J user@bastion1,user@bastion2 user@internal-server

# SCP through jump host
scp -o ProxyJump=user@bastion file.txt user@internal:/path/

# ✅ Best practice: configure in ~/.ssh/config (see Setup section)
```

### Workflow: Key Management

```bash
# List loaded keys in ssh-agent
ssh-add -l

# Add key to agent
ssh-add ~/.ssh/id_ed25519

# Add key with timeout (expires after N seconds)
ssh-add -t 3600 ~/.ssh/id_ed25519  # 1 hour

# Remove all keys from agent
ssh-add -D

# Start ssh-agent (if not running)
eval "$(ssh-agent -s)"
```

## Flag Gotchas

### Local (-L) vs Remote (-R) tunnel direction

```bash
# Think of it as: WHERE is the listening port?

# -L = Listening on LOCAL machine
# -L local_port:target_host:target_port user@tunnel_host
ssh -L 5432:db-server:5432 user@bastion -N
# Result: localhost:5432 → (through bastion) → db-server:5432

# -R = Listening on REMOTE machine
# -R remote_port:target_host:target_port user@tunnel_host
ssh -R 8080:localhost:3000 user@server -N
# Result: server:8080 → (back through tunnel) → localhost:3000

# ✅ Mnemonic: -L = Local listens, -R = Remote listens
```

### `-o StrictHostKeyChecking=no` — when to use

```bash
# ❌ INSECURE for production — disables host verification
ssh -o StrictHostKeyChecking=no user@server

# ✅ OK for ephemeral infrastructure (CI/CD, disposable VMs)
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null user@ci-runner

# ✅ For production: accept key once, verify fingerprint
ssh -o StrictHostKeyChecking=accept-new user@server
```

### `BatchMode=yes` for automation

```bash
# ❌ HANGS — prompts for password if key auth fails
ssh user@server

# ✅ BatchMode — fails immediately instead of prompting
ssh -o BatchMode=yes user@server 'echo connected'
# Exit code 255 = connection failed (no hang)
```

## Error Patterns

### `Permission denied (publickey)`

**Cause:** Key not accepted — wrong key, wrong permissions, or key not on server.

**Fix:**
```bash
# Check which key is being used
ssh -v user@server 2>&1 | grep "Offering"

# Check key permissions (MUST be restrictive)
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
chmod 700 ~/.ssh/

# Check server-side authorized_keys
ssh user@server 'cat ~/.ssh/authorized_keys'

# Force specific key
ssh -i ~/.ssh/specific_key user@server
```

### `Connection refused`

**Cause:** SSH server not running, wrong port, or firewall blocking.

**Fix:**
```bash
# Test port connectivity
nc -zv server 22

# Try alternate port
ssh -p 2222 user@server

# Check if server is running (if you have another access method)
sudo systemctl status sshd
```

### `Host key verification failed`

**Cause:** Server's host key changed (reinstalled, or man-in-the-middle).

**Fix:**
```bash
# Remove old key (only if you trust the server changed legitimately)
ssh-keygen -R server-hostname

# Then reconnect
ssh user@server  # Will prompt to accept new key

# For automation: accept new keys automatically
ssh -o StrictHostKeyChecking=accept-new user@server
```

### `Connection timed out`

**Cause:** Network issue, firewall, or server unreachable.

**Fix:**
```bash
# Quick timeout test
ssh -o ConnectTimeout=5 user@server

# Check with ping
ping -c 3 server

# Try through a different route/VPN
ssh -J bastion user@server
```

## Anti-Patterns

### Never use password auth in automation

```bash
# ❌ INSECURE and HANGS in non-interactive contexts
ssh user@server  # Prompts for password

# ✅ Use key-based auth
ssh -i ~/.ssh/deploy_key user@server

# ✅ For CI/CD: use ephemeral keys or certificates
```

### Never leave tunnels running without management

```bash
# ❌ Forgotten background tunnel
ssh -f -N -L 5432:db:5432 user@bastion  # Runs forever in background

# ✅ Use autossh for persistent tunnels (auto-reconnects)
autossh -M 0 -f -N -L 5432:db:5432 user@bastion

# ✅ Or use control sockets for manageable tunnels
ssh -M -S /tmp/tunnel-ctrl -fN -L 5432:db:5432 user@bastion
# Check: ssh -S /tmp/tunnel-ctrl -O check user@bastion
# Close: ssh -S /tmp/tunnel-ctrl -O exit user@bastion
```

### Never expose private keys

```bash
# ❌ NEVER commit keys or put them in environment variables
export SSH_KEY="-----BEGIN OPENSSH PRIVATE KEY-----..."

# ✅ Use ssh-agent or file references
ssh-add ~/.ssh/id_ed25519
# Or CI/CD secret → temporary file with strict permissions
```

## Composability

### SSH + rsync (better than scp)

```bash
# Sync directory (resumes, deletes removed files)
rsync -avz --delete -e ssh ./local-dir/ user@server:/remote-dir/

# Sync through bastion
rsync -avz -e "ssh -J user@bastion" ./local-dir/ user@target:/path/
```

### SSH + tar (transfer directories efficiently)

```bash
# Compress and transfer in one pipeline
tar czf - ./local-dir | ssh user@server 'tar xzf - -C /remote/path'

# Transfer from remote
ssh user@server 'tar czf - /var/log/app' | tar xzf - -C ./local-logs
```

### SSH + kubectl (access Kubernetes through tunnel)

```bash
# Tunnel to Kubernetes API
ssh -L 6443:k8s-master:6443 user@bastion -N &
# Then use kubectl with localhost
kubectl --server=https://localhost:6443 get pods
```

## Agent Constraints

### CRITICAL: SSH is interactive by default

```bash
# ❌ HANGS — waits for password or opens interactive shell
ssh user@server

# ✅ Run specific command (exits after command completes)
ssh -o BatchMode=yes -o ConnectTimeout=10 user@server 'hostname'

# ✅ For tunnels: use -N (no command) and run in background
ssh -fN -L 5432:db:5432 user@bastion

# ✅ Force non-interactive with BatchMode
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new user@server 'command'
# Fails immediately if key auth doesn't work (no password prompt)
```

### Tunnel management in automation

```bash
# Start tunnel in background with PID tracking
ssh -fN -L 5432:db:5432 user@bastion
TUNNEL_PID=$!

# Or use control socket for clean management
ssh -M -S /tmp/my-tunnel -fN -L 5432:db:5432 user@bastion
# Later:
ssh -S /tmp/my-tunnel -O exit user@bastion  # Clean shutdown
```

### Timeout everything

```bash
# Always set timeouts for agent use
ssh -o ConnectTimeout=10 \
    -o ServerAliveInterval=15 \
    -o ServerAliveCountMax=3 \
    -o BatchMode=yes \
    user@server 'command'
# Fails fast instead of hanging indefinitely
```

---
name: curl
description: "curl — HTTP requests, auth patterns, multipart uploads, API debugging, and response handling"
version: "8.x"
category: networking
---

# curl

> **Official docs:** https://curl.se/docs/ | **Reference:** https://curl.se/docs/manpage.html

curl transfers data with URLs. It's the universal API debugging and testing tool. The key challenges for agents are correct auth header formatting, multipart uploads, and response inspection patterns.

## Setup & Auth

```bash
# Verify (usually pre-installed)
curl --version

# Check supported protocols
curl --version | grep Protocols
```

## Core Workflows

### Workflow: Basic HTTP Methods

```bash
# GET (default)
curl https://api.example.com/users

# GET with headers
curl -H "Accept: application/json" https://api.example.com/users

# POST with JSON body
curl -X POST https://api.example.com/users \
  -H "Content-Type: application/json" \
  -d '{"name":"John","email":"john@example.com"}'

# PUT
curl -X PUT https://api.example.com/users/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Jane"}'

# PATCH
curl -X PATCH https://api.example.com/users/1 \
  -H "Content-Type: application/json" \
  -d '{"email":"jane@example.com"}'

# DELETE
curl -X DELETE https://api.example.com/users/1
```

### Workflow: Authentication

```bash
# Bearer token
curl -H "Authorization: Bearer $TOKEN" https://api.example.com/me

# Basic auth
curl -u username:password https://api.example.com/me

# API key in header
curl -H "X-API-Key: $API_KEY" https://api.example.com/data

# API key in query parameter
curl "https://api.example.com/data?api_key=$API_KEY"

# OAuth2 token request
curl -X POST https://auth.example.com/oauth/token \
  -d "grant_type=client_credentials" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET"
```

### Workflow: File Upload/Download

```bash
# Download file
curl -o filename.zip https://example.com/file.zip

# Download with original filename
curl -O https://example.com/file.zip

# Download with progress bar (default in terminal)
curl -# -O https://example.com/large-file.zip

# Upload file (multipart form)
curl -X POST https://api.example.com/upload \
  -F "file=@/path/to/file.pdf" \
  -F "description=My document"

# Upload file as raw body
curl -X PUT https://api.example.com/files/doc.pdf \
  -H "Content-Type: application/pdf" \
  --data-binary @/path/to/file.pdf

# Upload multiple files
curl -X POST https://api.example.com/upload \
  -F "file1=@photo1.jpg" \
  -F "file2=@photo2.jpg"
```

### Workflow: Response Inspection (Debugging)

```bash
# Show response headers
curl -i https://api.example.com/users

# Show ONLY response headers (HEAD request)
curl -I https://api.example.com/users

# Verbose output (request + response headers + body)
curl -v https://api.example.com/users

# Show timing info
curl -w "\nHTTP Code: %{http_code}\nTime Total: %{time_total}s\nTime Connect: %{time_connect}s\n" \
  -o /dev/null -s https://api.example.com/users

# Save response body and check status code
HTTP_CODE=$(curl -s -o response.json -w "%{http_code}" https://api.example.com/users)
echo "Status: $HTTP_CODE"
cat response.json | jq '.'

# Follow redirects
curl -L https://example.com/short-url

# Silent mode (no progress bar)
curl -s https://api.example.com/data | jq '.'
```

### Workflow: Common API Patterns

```bash
# JSON API with error handling
response=$(curl -s -w "\n%{http_code}" https://api.example.com/data)
body=$(echo "$response" | head -n -1)
code=$(echo "$response" | tail -n 1)
if [ "$code" -ne 200 ]; then
  echo "Error: HTTP $code"
  echo "$body"
fi

# Paginated API
page=1
while true; do
  result=$(curl -s "https://api.example.com/items?page=$page&per_page=100")
  count=$(echo "$result" | jq '.items | length')
  echo "$result" | jq '.items[]'
  [ "$count" -lt 100 ] && break
  page=$((page + 1))
done

# POST JSON from file
curl -X POST https://api.example.com/data \
  -H "Content-Type: application/json" \
  -d @payload.json

# POST with data from stdin
echo '{"key":"value"}' | curl -X POST https://api.example.com/data \
  -H "Content-Type: application/json" \
  -d @-
```

## Flag Gotchas

### `-d` sets Content-Type to form-urlencoded by default

```bash
# ❌ WRONG — sends as form data, not JSON
curl -X POST https://api.example.com/data \
  -d '{"name":"John"}'

# ✅ CORRECT — explicitly set Content-Type for JSON
curl -X POST https://api.example.com/data \
  -H "Content-Type: application/json" \
  -d '{"name":"John"}'
```

### `-d` strips newlines from data

```bash
# ❌ WRONG — newlines in file are stripped
curl -d @file-with-newlines.txt https://api.example.com/data

# ✅ CORRECT — use --data-binary to preserve exact content
curl --data-binary @file.txt https://api.example.com/data
```

### `-X POST` is not needed with `-d`

```bash
# ❌ REDUNDANT — -d already implies POST
curl -X POST -d '{"key":"val"}' https://api.example.com/data

# ✅ CLEANER — -d implies POST
curl -d '{"key":"val"}' -H "Content-Type: application/json" https://api.example.com/data

# ⚠️ But -X is needed for PUT, PATCH, DELETE
curl -X PUT -d '{"key":"val"}' -H "Content-Type: application/json" https://api.example.com/data
```

### `-s` vs `-S` vs `-sS`

```bash
# -s: silent (no progress bar, no errors)
curl -s https://api.example.com/data

# -S: show errors (even in silent mode)
curl -sS https://api.example.com/data  # Silent but shows errors

# ✅ Best practice for scripting
curl -sS https://api.example.com/data | jq '.'
```

## Error Patterns

### `curl: (6) Could not resolve host`

**Cause:** DNS resolution failed.

**Fix:**
```bash
# Check DNS
nslookup api.example.com
dig api.example.com

# Check if behind proxy
echo $HTTP_PROXY $HTTPS_PROXY

# Try with IP directly
curl -H "Host: api.example.com" http://1.2.3.4/endpoint
```

### `curl: (7) Failed to connect`

**Cause:** Server not reachable (firewall, wrong port, server down).

**Fix:**
```bash
# Test connectivity
nc -zv api.example.com 443

# Check if port is open
curl -v telnet://api.example.com:443

# Try without SSL (if testing locally)
curl http://localhost:3000/health
```

### `curl: (60) SSL certificate problem`

**Cause:** SSL/TLS certificate validation failed.

**Fix:**
```bash
# Check certificate details
curl -vI https://api.example.com 2>&1 | grep -A 5 "SSL certificate"

# ⚠️ Skip verification (ONLY for debugging, NEVER in production)
curl -k https://api.example.com/data

# Specify CA certificate
curl --cacert /path/to/ca-cert.pem https://api.example.com/data
```

## Anti-Patterns

### Never expose secrets in URLs

```bash
# ❌ LOGGED — tokens visible in shell history, server logs
curl "https://api.example.com/data?token=secret123"

# ✅ Use headers for auth
curl -H "Authorization: Bearer secret123" https://api.example.com/data
```

### Never use `-k` in production scripts

```bash
# ❌ INSECURE — disables ALL certificate verification
curl -k https://production-api.com/data

# ✅ Fix the certificate chain instead
curl --cacert /etc/ssl/certs/ca-certificates.crt https://production-api.com/data
```

## Composability

### curl + jq (API inspection)

```bash
# Fetch and format JSON
curl -s https://api.github.com/repos/jqlang/jq | jq '{stars: .stargazers_count, language}'

# Fetch, filter, and pipe
curl -s https://api.example.com/users | jq -r '.[].email' | sort
```

### curl + xargs (batch requests)

```bash
# Fetch multiple URLs
cat urls.txt | xargs -I{} -P4 curl -s -o /dev/null -w "{} %{http_code}\n" {}

# Delete multiple resources
seq 1 10 | xargs -I{} curl -X DELETE https://api.example.com/items/{}
```

### curl + aws (signed requests)

```bash
# AWS SigV4 signed request (curl 7.75+)
curl --aws-sigv4 "aws:amz:us-east-1:execute-api" \
  --user "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY" \
  https://api-id.execute-api.us-east-1.amazonaws.com/stage/resource
```

## Agent Constraints

### curl is non-interactive ✅

```bash
# curl has no interactive mode — always safe for agents
# All operations are fire-and-return

# ⚠️ Downloads can be large — always set max time
curl --max-time 30 -s https://api.example.com/data

# ⚠️ Disable progress bar for piping
curl -s https://api.example.com/data | jq '.'

# ⚠️ Limit response size
curl --max-filesize 10485760 -o file.bin https://example.com/large-file  # 10MB limit
```

---
name: jq
description: "jq — JSON filtering, select vs map, array operations, nested access, and composition with other CLI tools"
version: "1.7+"
category: dev-tools
---

# jq

> **Official docs:** https://jqlang.github.io/jq/manual/ | **Playground:** https://jqplay.org/

jq is the command-line JSON processor — the glue between any CLI that outputs JSON and your next command. Models frequently confuse `select` vs `map`, break array operations, and struggle with nested access patterns.

## Setup & Auth

```bash
# Installation (macOS)
brew install jq

# Installation (Linux)
sudo apt-get install jq  # Debian/Ubuntu
sudo yum install jq      # RHEL/CentOS

# Verify
jq --version
```

## Core Workflows

### Workflow: Basic Access

```bash
# Pretty-print JSON
echo '{"name":"app","version":"1.0"}' | jq '.'

# Access a field
echo '{"name":"app","version":"1.0"}' | jq '.name'
# Output: "app"

# Access nested field
echo '{"config":{"db":{"host":"localhost"}}}' | jq '.config.db.host'
# Output: "localhost"

# Raw output (no quotes)
echo '{"name":"app"}' | jq -r '.name'
# Output: app

# Access array element
echo '["a","b","c"]' | jq '.[0]'
# Output: "a"

# Array length
echo '[1,2,3,4,5]' | jq 'length'
# Output: 5
```

### Workflow: Array Operations

```bash
# Iterate over array elements
echo '[{"name":"a"},{"name":"b"}]' | jq '.[].name'
# Output:
# "a"
# "b"

# Map: transform each element (returns array)
echo '[1,2,3]' | jq 'map(. * 2)'
# Output: [2,4,6]

# Select: filter array elements (MUST use map or [.[]])
echo '[{"name":"a","active":true},{"name":"b","active":false}]' | \
  jq '[.[] | select(.active == true)]'
# Output: [{"name":"a","active":true}]

# Or equivalently with map:
echo '[{"name":"a","active":true},{"name":"b","active":false}]' | \
  jq 'map(select(.active == true))'

# Sort by field
echo '[{"name":"b","age":2},{"name":"a","age":1}]' | jq 'sort_by(.age)'

# First/Last N elements
echo '[1,2,3,4,5]' | jq '[:3]'   # First 3: [1,2,3]
echo '[1,2,3,4,5]' | jq '.[-2:]' # Last 2: [4,5]

# Unique values
echo '[1,2,2,3,3,3]' | jq 'unique'
# Output: [1,2,3]

# Group by field
echo '[{"type":"a","v":1},{"type":"b","v":2},{"type":"a","v":3}]' | \
  jq 'group_by(.type)'
```

### Workflow: Object Construction

```bash
# Create new object from fields
echo '{"first":"John","last":"Doe","age":30,"email":"j@d.com"}' | \
  jq '{name: (.first + " " + .last), email}'
# Output: {"name":"John Doe","email":"j@d.com"}

# Reshape array of objects
echo '[{"id":1,"name":"a","extra":"x"},{"id":2,"name":"b","extra":"y"}]' | \
  jq '.[] | {id, name}'

# Collect reshaped objects back into array
echo '[{"id":1,"name":"a","extra":"x"},{"id":2,"name":"b","extra":"y"}]' | \
  jq '[.[] | {id, name}]'

# Create TSV/CSV output
echo '[{"name":"a","count":5},{"name":"b","count":3}]' | \
  jq -r '.[] | [.name, .count] | @tsv'
# Output:
# a	5
# b	3

# CSV
echo '[{"name":"a","count":5},{"name":"b","count":3}]' | \
  jq -r '.[] | [.name, .count] | @csv'
```

### Workflow: Conditional Logic

```bash
# If-then-else
echo '{"status":"error","code":500}' | \
  jq 'if .status == "error" then "FAILED: \(.code)" else "OK" end'

# Alternative operator (default value)
echo '{"name":"app"}' | jq '.version // "unknown"'
# Output: "unknown"

# Null handling
echo '{"a":1,"b":null}' | jq '.b // "default"'
# Output: "default"

# Type checking
echo '{"val":"text"}' | jq '.val | type'
# Output: "string"
```

## Flag Gotchas

### `select` operates on single values, not arrays

```bash
# ❌ WRONG — select on array gives nothing useful
echo '[{"a":1},{"a":2}]' | jq 'select(.a > 1)'
# Error or unexpected output

# ✅ CORRECT — iterate first, then select
echo '[{"a":1},{"a":2}]' | jq '[.[] | select(.a > 1)]'
# Output: [{"a":2}]

# ✅ Or use map(select(...))
echo '[{"a":1},{"a":2}]' | jq 'map(select(.a > 1))'
# Output: [{"a":2}]
```

### `-r` (raw output) vs default (JSON strings)

```bash
# Without -r: strings have quotes
echo '{"name":"hello"}' | jq '.name'
# Output: "hello"

# With -r: raw string (no quotes)
echo '{"name":"hello"}' | jq -r '.name'
# Output: hello

# ✅ Always use -r when piping to other commands
echo '{"url":"https://example.com"}' | jq -r '.url' | xargs curl
```

### `-e` (exit status) for scripting

```bash
# Default: jq always exits 0 even if result is null/false
echo '{}' | jq '.missing' && echo "found"
# Output: null\nfound (misleading!)

# With -e: exits non-zero if result is null/false
echo '{}' | jq -e '.missing' && echo "found" || echo "not found"
# Output: null\nnot found (correct!)
```

### `--arg` for passing shell variables safely

```bash
# ❌ WRONG — shell variable interpolation breaks on special chars
NAME="hello world"
echo '{}' | jq ".name = \"$NAME\""  # Breaks on quotes in NAME

# ✅ CORRECT — use --arg for safe variable injection
NAME="hello world"
echo '{}' | jq --arg n "$NAME" '.name = $n'

# ✅ For numbers, use --argjson
COUNT=42
echo '{}' | jq --argjson c "$COUNT" '.count = $c'
```

## Error Patterns

### `null` output when field doesn't exist

**Cause:** Accessing a missing field returns `null`, not an error.

**Fix:**
```bash
# Check if field exists
echo '{"a":1}' | jq 'has("b")'
# Output: false

# Use alternative operator for defaults
echo '{"a":1}' | jq '.b // "default"'

# Use -e flag to catch in scripts
echo '{"a":1}' | jq -e '.b' || echo "field missing"
```

### `Cannot iterate over null`

**Cause:** Trying to iterate over a field that's null or missing.

**Fix:**
```bash
# ❌ Fails if .items is null
echo '{}' | jq '.items[]'

# ✅ Handle null with alternative operator
echo '{}' | jq '(.items // [])[]'

# ✅ Or use try
echo '{}' | jq 'try .items[]'
```

### `parse error: Invalid numeric literal`

**Cause:** Input is not valid JSON (often HTML error page or empty response).

**Fix:**
```bash
# Validate JSON first
echo "$RESPONSE" | jq empty 2>/dev/null && echo "valid" || echo "invalid JSON"

# Skip non-JSON lines (e.g., mixed output)
echo "$MIXED_OUTPUT" | jq -R 'fromjson? // empty'
```

## Anti-Patterns

### Never use string interpolation for building JSON

```bash
# ❌ BREAKS on special characters (quotes, backslashes)
echo "{\"name\":\"$USER_INPUT\"}" | jq '.'

# ✅ Use jq itself to build JSON safely
jq -n --arg name "$USER_INPUT" '{name: $name}'
```

### Never forget to collect results back into an array

```bash
# ❌ Outputs separate JSON values (not valid as a single JSON doc)
echo '[1,2,3]' | jq '.[] | . * 2'
# Output: 2\n4\n6 (three separate values)

# ✅ Wrap in array brackets
echo '[1,2,3]' | jq '[.[] | . * 2]'
# Output: [2,4,6] (one valid JSON array)
```

## Composability

### jq + aws

```bash
# Parse AWS CLI JSON output
aws ec2 describe-instances --output json | \
  jq -r '.Reservations[].Instances[] | [.InstanceId, .State.Name, .PrivateIpAddress] | @tsv'

# Filter Lambda functions by runtime
aws lambda list-functions | \
  jq -r '.Functions[] | select(.Runtime == "python3.12") | .FunctionName'
```

### jq + kubectl

```bash
# Get all container images in cluster
kubectl get pods -A -o json | \
  jq -r '.items[].spec.containers[].image' | sort -u

# Get pods with restart count > 0
kubectl get pods -A -o json | \
  jq -r '.items[] | select(.status.containerStatuses[]?.restartCount > 0) | [.metadata.namespace, .metadata.name] | @tsv'
```

### jq + curl

```bash
# Parse API response
curl -s https://api.github.com/repos/jqlang/jq | \
  jq '{stars: .stargazers_count, forks: .forks_count, language: .language}'

# Handle paginated APIs
curl -s "https://api.example.com/items?page=1" | jq '.items[]'
```

### jq + gh

```bash
# Parse GitHub CLI JSON output
gh pr list --json number,title,author | \
  jq -r '.[] | "#\(.number) \(.title) (@\(.author.login))"'
```

## Agent Constraints

### jq is non-interactive ✅

```bash
# jq has no interactive mode — always safe for agents
# All operations are pipes — input in, output out

# For files instead of pipes:
jq '.' file.json                    # Read from file
jq '.' file.json > output.json     # Write to file

# ⚠️ Cannot edit files in-place — use sponge or temp file
jq '.version = "2.0"' config.json > tmp.json && mv tmp.json config.json
```

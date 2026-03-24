# redis-cli — Redis Command-Line Interface

## Connection

```bash
# Local default (127.0.0.1:6379)
redis-cli

# Remote connection
redis-cli -h HOST -p 6379

# With password (AUTH)
redis-cli -h HOST -p 6379 -a PASSWORD

# With username + password (Redis 6+ ACL)
redis-cli -h HOST -p 6379 --user USERNAME -a PASSWORD

# TLS connection
redis-cli -h HOST -p 6380 --tls --cert client.crt --key client.key --cacert ca.crt

# Select database number (default is 0)
redis-cli -n 3

# Connection URI
redis-cli -u redis://user:password@host:6379/0
redis-cli -u rediss://user:password@host:6380/0  # TLS
```

> **⚠️ `-a PASSWORD` on command line** — Exposes password in process list and shell history. Prefer `REDISCLI_AUTH` environment variable or interactive `AUTH` command.

```bash
export REDISCLI_AUTH=mysecretpassword
redis-cli -h host
```

## Non-Interactive Commands

```bash
# Run single command
redis-cli -h host SET mykey "hello"
redis-cli -h host GET mykey

# Pipe multiple commands
echo -e "SET key1 val1\nSET key2 val2\nGET key1" | redis-cli -h host

# Mass insertion (Redis protocol format)
redis-cli -h host --pipe < commands.txt

# Pipe mode generates Redis protocol (RESP) — use for bulk loading:
# Each line in commands.txt should be a Redis command
cat data.txt | redis-cli --pipe

# Repeat a command N times
redis-cli -h host -r 100 -i 0.1 PING  # 100 PINGs, 0.1s interval

# Output in CSV format
redis-cli -h host --csv LRANGE mylist 0 -1

# Output in JSON format (Redis 7+)
redis-cli -h host --json GET mykey

# Raw output (no quoting, useful for scripts)
redis-cli -h host --raw GET mykey

# Scan all keys matching pattern (safe alternative to KEYS)
redis-cli -h host --scan --pattern "user:*"
redis-cli -h host --scan --pattern "session:*" --count 100
```

## Key Operations

```bash
# String
SET key "value"
SET key "value" EX 3600           # Expires in 3600 seconds
SET key "value" NX                # Only if key doesn't exist
GET key
MSET k1 "v1" k2 "v2" k3 "v3"    # Set multiple
MGET k1 k2 k3                    # Get multiple
INCR counter                      # Atomic increment
INCRBY counter 5

# Hash
HSET user:1 name "Alice" email "a@b.com"
HGET user:1 name
HGETALL user:1
HDEL user:1 email

# List
LPUSH queue "task1"               # Push to head
RPUSH queue "task2"               # Push to tail
LPOP queue                        # Pop from head
RPOP queue                        # Pop from tail
LRANGE queue 0 -1                 # Get all elements
LLEN queue                        # Length

# Set
SADD tags "python" "redis" "cli"
SMEMBERS tags
SISMEMBER tags "redis"
SCARD tags                        # Count

# Sorted Set
ZADD leaderboard 100 "alice" 200 "bob"
ZRANGE leaderboard 0 -1 WITHSCORES
ZRANK leaderboard "alice"
ZRANGEBYSCORE leaderboard 50 150

# Key management
DEL key                           # Delete
EXISTS key                        # Check existence (returns 0 or 1)
TYPE key                          # Get type
TTL key                           # Time to live (-1 = no expiry, -2 = doesn't exist)
EXPIRE key 3600                   # Set expiry
PERSIST key                       # Remove expiry
RENAME oldkey newkey
```

## Debugging & Monitoring

```bash
# Real-time command monitor (streams all commands — use sparingly in production)
redis-cli MONITOR

# Server info (all sections)
redis-cli INFO

# Specific section
redis-cli INFO memory
redis-cli INFO replication
redis-cli INFO clients
redis-cli INFO stats

# Memory usage of a specific key
redis-cli MEMORY USAGE mykey

# Slow log (commands exceeding slowlog-log-slower-than threshold)
redis-cli SLOWLOG GET 10
redis-cli SLOWLOG LEN
redis-cli SLOWLOG RESET

# Client list (connected clients)
redis-cli CLIENT LIST

# Kill a client by ID
redis-cli CLIENT KILL ID 42

# Latency diagnostics
redis-cli --latency               # Continuous latency sampling
redis-cli --latency-history       # Latency over time (15s intervals)
redis-cli --latency-dist          # Latency spectrum/distribution

# Check memory fragmentation
redis-cli INFO memory | grep mem_fragmentation_ratio
```

## Persistence & Snapshots

```bash
# Trigger RDB snapshot (background)
redis-cli BGSAVE

# Check last save time
redis-cli LASTSAVE

# Trigger AOF rewrite (background)
redis-cli BGREWRITEAOF

# Get current persistence config
redis-cli CONFIG GET save
redis-cli CONFIG GET appendonly

# Enable AOF at runtime
redis-cli CONFIG SET appendonly yes

# Check RDB/AOF status
redis-cli INFO persistence
```

## Pub/Sub

```bash
# Subscribe to channel(s)
redis-cli SUBSCRIBE news alerts

# Subscribe to pattern
redis-cli PSUBSCRIBE "user:*"

# Publish (from another terminal)
redis-cli PUBLISH news "Breaking news!"

# Check active channels/subscribers
redis-cli PUBSUB CHANNELS
redis-cli PUBSUB NUMSUB news
```

## Cluster Operations

```bash
# Cluster info
redis-cli CLUSTER INFO
redis-cli CLUSTER NODES

# Connect to cluster (follow redirects automatically)
redis-cli -c -h host -p 7000

# Create cluster (Redis 5+)
redis-cli --cluster create host1:7000 host1:7001 host2:7000 host2:7001 host3:7000 host3:7001 \
  --cluster-replicas 1

# Check cluster health
redis-cli --cluster check host:7000

# Reshard slots
redis-cli --cluster reshard host:7000

# Add/remove nodes
redis-cli --cluster add-node new_host:7000 existing_host:7000
redis-cli --cluster del-node host:7000 NODE_ID

# Fix cluster (repair slot allocation issues)
redis-cli --cluster fix host:7000
```

## Lua Scripting

```bash
# Run inline Lua script
redis-cli EVAL "return redis.call('GET', KEYS[1])" 1 mykey

# Atomic check-and-set
redis-cli EVAL "
  local val = redis.call('GET', KEYS[1])
  if val == ARGV[1] then
    redis.call('SET', KEYS[1], ARGV[2])
    return 1
  end
  return 0
" 1 mykey "old_value" "new_value"

# Load script and get SHA
redis-cli SCRIPT LOAD "return redis.call('GET', KEYS[1])"

# Execute by SHA (faster for repeated calls)
redis-cli EVALSHA <sha> 1 mykey

# Check if script exists
redis-cli SCRIPT EXISTS <sha>

# Flush all cached scripts
redis-cli SCRIPT FLUSH
```

## Common Patterns

### Flush Data (Careful!)

```bash
# Flush current database
redis-cli FLUSHDB

# Flush ALL databases
redis-cli FLUSHALL

# Async flush (non-blocking, Redis 4+)
redis-cli FLUSHDB ASYNC
redis-cli FLUSHALL ASYNC
```

### Scan Keys Safely

```bash
# NEVER use KEYS in production (blocks server)
# ❌ redis-cli KEYS "user:*"

# ✅ Use SCAN instead (cursor-based, non-blocking)
redis-cli --scan --pattern "user:*"

# With count hint (not a hard limit)
redis-cli --scan --pattern "session:*" --count 1000

# Count matching keys
redis-cli --scan --pattern "cache:*" | wc -l

# Delete matching keys safely
redis-cli --scan --pattern "temp:*" | xargs redis-cli DEL
```

### Export/Import

```bash
# Dump key in RDB format
redis-cli DUMP mykey

# Restore key from dump
redis-cli RESTORE mykey 0 "\x00\x05hello..."

# Copy all keys between instances
redis-cli -h source --scan --pattern "*" | while read key; do
  redis-cli -h source DUMP "$key" | head -c -1 | \
  redis-cli -h target RESTORE "$key" 0 - REPLACE
done

# Use redis-cli --rdb to download full RDB
redis-cli -h host --rdb dump.rdb
```

## Gotchas

1. **`KEYS` command blocks** — `KEYS *` scans the entire keyspace and blocks Redis. Always use `SCAN` in production.
2. **`-a` exposes password** — Use `REDISCLI_AUTH` env var instead of `-a` on the command line.
3. **`-c` for cluster mode** — Without `-c`, commands hitting wrong slots return `MOVED` errors instead of auto-redirecting.
4. **`MONITOR` is expensive** — Streams every command in real-time. Significant performance impact in production; use for debugging only.
5. **`DEL` is blocking** — For large keys (millions of elements), use `UNLINK` (async delete, Redis 4+) to avoid blocking.
6. **`FLUSHDB`/`FLUSHALL` are irreversible** — No confirmation prompt. Consider using `FLUSHDB ASYNC` to at least avoid blocking.
7. **Pub/Sub is fire-and-forget** — Messages are not persisted. If no subscriber is listening, the message is lost. Use Redis Streams for persistent messaging.
8. **`--pipe` expects RESP format** — For mass insertion, generate Redis protocol format or use plain commands. Errors are reported at the end, not inline.

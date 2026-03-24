# psql — PostgreSQL Interactive Terminal

## Connection

```bash
# Basic connection
psql -h HOST -p 5432 -U USER -d DATABASE

# Connection string (URI format)
psql "postgresql://user:password@host:5432/dbname?sslmode=require"

# Connect via Unix socket (local)
psql -U postgres dbname

# Connect and run single command
psql -h host -U user -d db -c "SELECT version();"

# Connect and run SQL file
psql -h host -U user -d db -f script.sql
```

### Environment Variables

```bash
export PGHOST=localhost
export PGPORT=5432
export PGUSER=myuser
export PGPASSWORD=mypass      # or use ~/.pgpass file
export PGDATABASE=mydb

# Then just:
psql
```

### Password File (~/.pgpass)

```
# Format: hostname:port:database:username:password
localhost:5432:mydb:myuser:mypass
*:5432:*:admin:adminpass

# Must be chmod 600
chmod 600 ~/.pgpass
```

## Non-Interactive Queries

```bash
# Single query, output only data (no headers/footers)
psql -h host -U user -d db -t -A -c "SELECT id, name FROM users;"

# Tab-separated output
psql -h host -U user -d db -t -A -F $'\t' -c "SELECT * FROM users;"

# CSV output (PostgreSQL 12+)
psql -h host -U user -d db -c "COPY (SELECT * FROM users) TO STDOUT WITH CSV HEADER;"

# Pipe SQL from stdin
echo "SELECT count(*) FROM orders;" | psql -h host -U user -d db -t

# Run multiple statements from file
psql -h host -U user -d db -f migration.sql -v ON_ERROR_STOP=1

# Variable substitution
psql -v table_name='users' -c "SELECT * FROM :table_name LIMIT 5;"
```

### Output Formatting Flags

| Flag | Effect |
|------|--------|
| `-t` | Tuples only (no headers/footers) |
| `-A` | Unaligned output (no padding) |
| `-F','` | Set field separator (e.g., comma) |
| `-H` | HTML table output |
| `-x` | Expanded display (one column per line) |
| `--csv` | CSV output mode (v12+) |
| `-q` | Quiet (suppress informational messages) |

## Meta-Commands (Inside psql)

### Navigation

```sql
\l              -- List all databases
\c dbname       -- Connect to database
\dt             -- List tables in current schema
\dt schema.*    -- List tables in specific schema
\dt+            -- List tables with size info
\d tablename    -- Describe table (columns, types, indexes)
\d+ tablename   -- Describe with storage and comments
\di             -- List indexes
\dv             -- List views
\dm             -- List materialized views
\df             -- List functions
\dn             -- List schemas
\du             -- List roles/users
\dp             -- List table privileges
```

### Query Helpers

```sql
\x              -- Toggle expanded display
\x auto         -- Auto-expand for wide results
\timing         -- Toggle query timing display
\e              -- Open last query in $EDITOR
\g              -- Re-execute last query
\g output.txt   -- Execute last query and save to file
\watch 5        -- Re-run last query every 5 seconds
\!              -- Execute shell command (e.g., \! ls)
```

### Import/Export

```sql
-- Copy table to CSV file
\copy users TO '/tmp/users.csv' WITH CSV HEADER

-- Copy CSV file to table
\copy users FROM '/tmp/users.csv' WITH CSV HEADER

-- Copy with custom delimiter
\copy users TO '/tmp/users.tsv' WITH DELIMITER E'\t' HEADER

-- Copy specific columns
\copy users(name,email) FROM '/tmp/partial.csv' WITH CSV HEADER
```

> **⚠️ \copy vs COPY**: `\copy` runs client-side (reads/writes local files). `COPY` runs server-side (reads/writes files on the DB server). In most SWE workflows, use `\copy`.

## Backup & Restore

### pg_dump (Single Database)

```bash
# Plain SQL dump
pg_dump -h host -U user dbname > backup.sql

# Custom format (compressed, supports parallel restore)
pg_dump -h host -U user -Fc dbname > backup.dump

# Directory format (parallel dump)
pg_dump -h host -U user -Fd -j 4 dbname -f backup_dir/

# Dump specific tables
pg_dump -h host -U user -t users -t orders dbname > tables.sql

# Dump schema only (no data)
pg_dump -h host -U user --schema-only dbname > schema.sql

# Dump data only (no DDL)
pg_dump -h host -U user --data-only dbname > data.sql

# Exclude tables
pg_dump -h host -U user --exclude-table='*_log' dbname > backup.sql
```

### pg_restore

```bash
# Restore custom/directory format
pg_restore -h host -U user -d dbname backup.dump

# Restore with parallel jobs
pg_restore -h host -U user -d dbname -j 4 backup_dir/

# Restore specific table from dump
pg_restore -h host -U user -d dbname -t users backup.dump

# Clean (drop) objects before restore
pg_restore -h host -U user -d dbname --clean --if-exists backup.dump

# Restore plain SQL files (use psql, not pg_restore)
psql -h host -U user -d dbname < backup.sql
```

### pg_dumpall (All Databases + Globals)

```bash
# Full cluster dump (all databases, roles, tablespaces)
pg_dumpall -h host -U postgres > full_backup.sql

# Globals only (roles, tablespaces)
pg_dumpall -h host -U postgres --globals-only > globals.sql
```

## Common Patterns

### Check Active Connections

```bash
psql -h host -U user -d db -c "
  SELECT pid, usename, application_name, state, query_start, query
  FROM pg_stat_activity
  WHERE state = 'active'
  ORDER BY query_start;
"
```

### Kill a Query

```bash
# Cancel query (graceful)
psql -c "SELECT pg_cancel_backend(PID);"

# Terminate connection (forceful)
psql -c "SELECT pg_terminate_backend(PID);"
```

### Database Size

```bash
psql -c "SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname))
         FROM pg_database ORDER BY pg_database_size(pg_database.datname) DESC;"
```

### Table Sizes

```bash
psql -c "SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
         FROM pg_catalog.pg_statio_user_tables
         ORDER BY pg_total_relation_size(relid) DESC LIMIT 20;"
```

### Check and Wait for Replication

```bash
psql -c "SELECT client_addr, state, sent_lsn, replay_lsn,
         sent_lsn - replay_lsn AS replication_lag
         FROM pg_stat_replication;"
```

## Gotchas

1. **`-v ON_ERROR_STOP=1`** — Always use in scripts. Without it, psql continues executing after errors.
2. **`\copy` vs `COPY`** — `\copy` is client-side (local files), `COPY` is server-side. They look similar but behave very differently.
3. **Quoting in `-c`** — Use double quotes for the shell, single quotes for SQL: `psql -c "SELECT 'hello';"`.
4. **Transaction behavior** — By default, psql auto-commits each statement. Use `BEGIN;`/`COMMIT;` or `psql --single-transaction` for atomicity.
5. **pg_restore needs custom format** — `pg_restore` cannot restore plain SQL files. Use `psql -f` for `.sql` files and `pg_restore` for `-Fc`/`-Fd` dumps.
6. **`--clean` doesn't create the DB** — It drops/recreates objects *inside* the database. The target database must already exist.

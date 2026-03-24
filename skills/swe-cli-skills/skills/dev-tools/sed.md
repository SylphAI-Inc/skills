# sed — Stream Editor

## Basic Syntax

```bash
# In-place edit (GNU Linux)
sed -i 's/old/new/g' file.txt

# In-place edit (macOS/BSD) — requires empty string for backup
sed -i '' 's/old/new/g' file.txt

# Portable in-place edit (works on both)
sed -i.bak 's/old/new/g' file.txt && rm file.txt.bak
```

> **⚠️ The #1 agent gotcha:** `sed -i` behaves DIFFERENTLY on macOS vs Linux. On macOS, `-i` requires an argument (backup extension). Use `-i ''` for no backup on macOS, or `-i.bak` portably.

## Substitution

```bash
# Replace first occurrence per line
sed 's/foo/bar/' file.txt

# Replace ALL occurrences per line
sed 's/foo/bar/g' file.txt

# Replace only on specific line number
sed '5s/foo/bar/' file.txt

# Replace on line range
sed '10,20s/foo/bar/g' file.txt

# Replace on lines matching pattern
sed '/^#/s/foo/bar/g' file.txt

# Case-insensitive replace (GNU only)
sed 's/foo/bar/gI' file.txt

# Use different delimiter (useful when pattern contains /)
sed 's|/usr/local|/opt|g' file.txt
sed 's#http://#https://#g' file.txt

# Replace with capture groups
sed 's/\(.*\)=\(.*\)/\2=\1/' file.txt       # swap key=value
sed -E 's/(.*)=(.*)/\2=\1/' file.txt          # extended regex (cleaner)

# Replace with newline
sed 's/;/\n/g' file.txt          # GNU
sed 's/;/\'$'\n/g' file.txt      # macOS/BSD
```

## Line Operations

```bash
# Print specific line
sed -n '5p' file.txt

# Print line range
sed -n '10,20p' file.txt

# Print lines matching pattern
sed -n '/ERROR/p' file.txt

# Delete specific line
sed '5d' file.txt

# Delete line range
sed '10,20d' file.txt

# Delete lines matching pattern
sed '/^$/d' file.txt              # delete empty lines
sed '/^#/d' file.txt              # delete comment lines
sed '/DEBUG/d' file.txt           # delete lines with DEBUG

# Delete all EXCEPT matching lines
sed '/KEEP/!d' file.txt

# Insert line before match
sed '/pattern/i\new line before' file.txt       # GNU
sed '/pattern/i\'$'\n''new line before' file.txt # macOS

# Insert line after match
sed '/pattern/a\new line after' file.txt         # GNU
sed '/pattern/a\'$'\n''new line after' file.txt   # macOS

# Replace entire line matching pattern
sed '/^old_config/c\new_config=value' file.txt
```

## Multiple Operations

```bash
# Chain with -e
sed -e 's/foo/bar/g' -e 's/baz/qux/g' file.txt

# Or use semicolons (GNU)
sed 's/foo/bar/g; s/baz/qux/g' file.txt

# From a script file
sed -f commands.sed file.txt
```

## Common Patterns

### Extract Between Patterns

```bash
# Print lines between two patterns (inclusive)
sed -n '/START/,/END/p' file.txt

# Print lines between two patterns (exclusive)
sed -n '/START/,/END/{/START/!{/END/!p}}' file.txt
```

### Add/Remove Prefix/Suffix

```bash
# Add prefix to every line
sed 's/^/PREFIX: /' file.txt

# Add suffix to every line
sed 's/$/ SUFFIX/' file.txt

# Remove first N characters
sed 's/^.\{3\}//' file.txt

# Remove trailing whitespace
sed 's/[[:space:]]*$//' file.txt
```

### Config File Edits

```bash
# Uncomment a line
sed -i 's/^#\(some_setting\)/\1/' config.conf

# Comment out a line
sed -i 's/^\(some_setting\)/#\1/' config.conf

# Change config value
sed -i 's/^max_connections=.*/max_connections=200/' config.conf

# Add line after match (if not already present)
grep -q 'new_setting' config.conf || sed -i '/\[section\]/a new_setting=value' config.conf
```

### Pipeline Usage

```bash
# Pipe from other commands
cat file.txt | sed 's/foo/bar/g'
echo "hello world" | sed 's/world/universe/'
grep "pattern" file.txt | sed 's/prefix: //'

# Combine with other tools
find . -name "*.py" -exec sed -i 's/old_func/new_func/g' {} +
```

## Extended Regex (-E)

```bash
# Use -E (or -r on GNU) for extended regex
sed -E 's/[0-9]{3}-[0-9]{4}/XXX-XXXX/g' file.txt

# Alternation
sed -E 's/(error|warning|critical)/ALERT/g' file.txt

# Optional groups
sed -E 's/colou?r/color/g' file.txt

# Non-greedy is NOT supported in sed
# Use more specific patterns instead of .*?
```

## Gotchas

1. **macOS vs Linux `-i`** — macOS requires `-i ''` (with empty string), Linux uses `-i` alone. Use `-i.bak` for portability.
2. **No non-greedy matching** — sed doesn't support `.*?`. Use `[^delimiter]*` instead: `s/<[^>]*>//g` to strip HTML tags.
3. **Newlines in replacement** — `\n` in replacement only works in GNU sed. On macOS, use literal newline with `$'\n'`.
4. **Delimiter conflicts** — If your pattern contains `/`, use a different delimiter: `s|path/to|new/path|g`.
5. **In-place + no output** — `sed -i` with no match still rewrites the file (updates mtime). Check before running in loops.
6. **Backslash in replacement** — Use `\\` for literal backslash, `\1` for capture groups. Easy to confuse.
7. **Empty regex** — `sed 's//replacement/'` reuses the last regex. This is rarely what you want.
8. **Character classes** — Use `[[:space:]]` not `\s`, `[[:digit:]]` not `\d`. sed uses POSIX classes, not Perl.

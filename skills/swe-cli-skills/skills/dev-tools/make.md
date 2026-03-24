# make — Build Automation

## Basic Syntax

```makefile
# Makefile
target: dependencies
	command    # MUST be a real TAB character, not spaces

# Example
build: src/main.c src/utils.c
	gcc -o app src/main.c src/utils.c

clean:
	rm -f app
```

> **⚠️ The #1 make gotcha:** Indentation MUST be real tabs, not spaces. Spaces cause `Makefile:N: *** missing separator. Stop.` — this error is invisible in most editors.

## Running Make

```bash
# Run default target (first target in file)
make

# Run specific target
make build
make test
make clean

# Use specific Makefile
make -f custom.mk

# Dry run (show commands without executing)
make -n

# Silent mode (don't print commands)
make -s

# Override variable
make CC=clang
make DEBUG=1

# Parallel execution
make -j4           # 4 parallel jobs
make -j$(nproc)    # all available cores

# Keep going after errors
make -k

# Print database of rules
make -p

# Change directory
make -C subdir/
```

## Variables

```makefile
# Simple assignment (expanded when used)
CC = gcc
CFLAGS = -Wall -Wextra

# Immediate assignment (expanded at definition)
CC := gcc
BUILD_DIR := build

# Conditional assignment (only if not already set)
CC ?= gcc

# Append
CFLAGS += -O2

# Using variables
build:
	$(CC) $(CFLAGS) -o app src/main.c

# Automatic variables
# $@ = target name
# $< = first dependency
# $^ = all dependencies
# $* = stem of pattern match
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@
```

### Environment Variables

```bash
# Override from command line (highest priority)
make CFLAGS="-O3"

# Export to sub-makes
export CC = gcc

# Pass all variables to sub-makes
$(MAKE) -C subdir/

# Shell environment variables are available
# but Makefile variables take precedence
```

## Phony Targets

```makefile
# Declare targets that aren't files
.PHONY: all build test clean install

all: build test

build:
	go build ./...

test:
	go test ./...

clean:
	rm -rf bin/

install: build
	cp bin/app /usr/local/bin/
```

> **⚠️ Without `.PHONY`**, if a file named `test` or `clean` exists, make skips the target (thinks it's up-to-date).

## Pattern Rules

```makefile
# Compile any .c file to .o
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# Compile any .ts file to .js
%.js: %.ts
	npx tsc $<

# Generic rule with stem
build/%: src/%.go
	go build -o $@ $<
```

## Common Project Makefiles

### Go Project

```makefile
.PHONY: all build test lint clean run

BINARY := myapp
BUILD_DIR := bin

all: lint test build

build:
	go build -o $(BUILD_DIR)/$(BINARY) ./cmd/$(BINARY)

test:
	go test -v -race ./...

lint:
	golangci-lint run

clean:
	rm -rf $(BUILD_DIR)

run: build
	./$(BUILD_DIR)/$(BINARY)
```

### Python Project

```makefile
.PHONY: install test lint format clean

install:
	pip install -e ".[dev]"

test:
	pytest -v

lint:
	ruff check .
	mypy .

format:
	ruff format .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache dist/
```

### Node.js Project

```makefile
.PHONY: install build test lint clean

install:
	npm ci

build: install
	npm run build

test: install
	npm test

lint: install
	npm run lint

clean:
	rm -rf node_modules dist
```

### Docker Project

```makefile
.PHONY: build push run stop

IMAGE := myapp
TAG := $(shell git rev-parse --short HEAD)

build:
	docker build -t $(IMAGE):$(TAG) -t $(IMAGE):latest .

push: build
	docker push $(IMAGE):$(TAG)
	docker push $(IMAGE):latest

run:
	docker run -d --name $(IMAGE) -p 8080:8080 $(IMAGE):latest

stop:
	docker stop $(IMAGE) && docker rm $(IMAGE)
```

## Conditionals

```makefile
# Check if variable is set
ifdef DEBUG
  CFLAGS += -g -DDEBUG
else
  CFLAGS += -O2
endif

# Check OS
ifeq ($(shell uname), Darwin)
  SED_INPLACE := sed -i ''
else
  SED_INPLACE := sed -i
endif

# Check if command exists
HAS_DOCKER := $(shell command -v docker 2>/dev/null)
check-docker:
ifndef HAS_DOCKER
	$(error "docker is not installed")
endif
```

## Functions

```makefile
# Wildcard — find files
SRCS := $(wildcard src/*.c)
OBJS := $(patsubst src/%.c, build/%.o, $(SRCS))

# Shell — run shell command
GIT_HASH := $(shell git rev-parse --short HEAD)
DATE := $(shell date +%Y-%m-%d)

# Substitution
OBJS := $(SRCS:.c=.o)

# Filter
C_FILES := $(filter %.c, $(SRCS))
NON_TEST := $(filter-out %_test.go, $(GO_FILES))

# Word operations
FIRST := $(firstword $(SRCS))
LAST := $(lastword $(SRCS))
```

## Multi-Line Commands

```makefile
# Each line runs in a separate shell!
# This FAILS:
wrong:
	cd subdir
	pwd          # Still in original directory!

# Use && or backslash continuation:
right:
	cd subdir && pwd

also-right:
	cd subdir && \
	pwd && \
	make build

# Or use .ONESHELL (GNU make 3.82+):
.ONESHELL:
oneshell-target:
	cd subdir
	pwd
	make build
```

## Gotchas

1. **Tabs not spaces** — Recipe lines MUST start with a tab character. Spaces cause `*** missing separator`. Configure your editor for Makefiles.
2. **Each line is a separate shell** — `cd dir` on one line doesn't affect the next. Use `&&` or `\` continuation.
3. **`.PHONY` is essential** — Without it, targets named `test`, `clean`, etc. won't run if a file with that name exists.
4. **`=` vs `:=`** — `=` is recursive (re-evaluated each use), `:=` is immediate (evaluated once). Use `:=` for expensive shell calls.
5. **`$` in shell commands** — Use `$$` to pass `$` to the shell: `echo $$HOME`, `awk '{print $$1}'`.
6. **`make` vs `$(MAKE)`** — Always use `$(MAKE)` for recursive make calls. It preserves flags and job server.
7. **Order of targets** — The first target is the default. Convention: name it `all`.
8. **Parallel safety (`-j`)** — If targets share output files or have hidden dependencies, parallel builds can race. Declare all dependencies explicitly.

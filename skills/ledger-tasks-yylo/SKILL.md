---
name: ledger-tasks-yylo
description: Operate a YYLO Ledger Kanban board from the command line with the yy ledger CLI - create, list, search, get, mark, update, and archive tasks with required response receipts, manage blocked-by dependencies, compute ready and ordered work, and emit JSON, ndjson, XML, or table output
author: yylo-dev
version: 1.0.0
---

# YYLO Ledger Task Management

Use this skill when an agent works in a repository whose task state is tracked by a YYLO Ledger board. All board operations run through the `yy ledger` command of the YYLO CLI (`yy kanban` is a labelled compatibility alias). The board lives under the repository's `.juno_task/` directory as plain, hash-chained Markdown; the CLI is the only sanctioned mutation path.

## When to Use

- The repository contains a `.juno_task/` directory (a YYLO Ledger board is present).
- The user asks to create, find, update, or finish tasks, or mentions the Kanban board, task state, or task dependencies.
- A workflow needs dependency-aware task selection (which tasks are ready now, in what order).
- Scripts or reports need machine-readable task output (JSON, ndjson, XML).

## Prerequisites

- Node.js and the YYLO CLI installed globally:

```bash
npm install --global @yylo/cli
yy ledger --version
```

The CLI is MIT-licensed and open source ([yylo-dev/yylo](https://github.com/yylo-dev/yylo)); the task runtime is [yylo-dev/yylo-ledger](https://github.com/yylo-dev/yylo-ledger). This skill is non-functional without the CLI.

## Instructions

Read current task state before mutating it, preserve mutation receipts where offered, and never edit board files directly to change lifecycle state. Command help is authoritative for the installed runtime: when unsure, run `yy ledger --help` first.

### Create a task

```bash
yy ledger create "Task description here" --status backlog --tags feature,backend
```

Options: `--status` (backlog|todo|in_progress|done), `--tags` (comma/space-separated), `--blocked-by` (task IDs), `--related-tasks` (task IDs).

### List and search

```bash
yy ledger list --limit 5 --sort asc
yy ledger list --status todo,in_progress --limit 10
yy ledger search "refund handler" --status in_progress
```

### Inspect one task

```bash
yy ledger get TASK_ID
```

Shows full task detail including description, status, tags, dependencies, and response receipts.

### Mark status (receipt required)

```bash
yy ledger mark TASK_ID in_progress --response "Starting implementation after plan review"
yy ledger mark TASK_ID done --response "Validated: tests green, commit abc1234"
```

Every status change requires a `--response` receipt explaining why the state changed; keep receipts factual and short.

### Update fields

```bash
yy ledger update TASK_ID --description "Revised scope: refunds only" --tags feature,refunds
```

### Dependency management

```bash
yy ledger deps TASK_ID --add TASK_ID_2          # TASK_ID now blocked by TASK_ID_2
yy ledger deps TASK_ID --remove TASK_ID_2
yy ledger ready                                # tasks whose blockers are all done
yy ledger order                                # topological execution order for ready work
```

Prefer `ready` and `order` over hand-picking tasks: they encode the dependency graph instead of guessing.

### Archive

```bash
yy ledger archive TASK_ID
```

Archiving moves a finished task out of the default board view; it does not delete history.

### Machine-readable output

```bash
yy ledger list --format json
yy ledger list --format ndjson
yy ledger ready --format json
```

Use `--format` for scripting and reporting; the default table output is for humans.

## Best Practices

- Mutate task state only through the CLI; direct edits to `.juno_task/` files break the hash chain.
- Record a meaningful `--response` receipt on every mark: future readers (and audits) rely on them.
- Check `ready`/`order` before claiming a task; a blocked task must not be started.
- Keep one task per unit of work; use `--tags` and `--related-tasks` for grouping instead of overloading descriptions.

## Source and Attribution

Vendored and adapted from the canonical skill pack [yylo-dev/yylo-skills](https://github.com/yylo-dev/yylo-skills) (same `ledger-tasks-yylo` slug and content family, MIT). Submitted by the YYLO team; the skill wraps the documented `yy ledger` surface of the YYLO CLI.

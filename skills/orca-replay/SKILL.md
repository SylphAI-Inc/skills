---
name: orca-replay
description: Operational workflow for the `orca` CLI (OrcaReplay) — record an agent run at the model-provider boundary, read the timeline, follow the causal chain to one event, replay the run offline, and diff two runs. Use when debugging an agent run that already finished, when a failure needs to be reproduced without spending provider calls, or when two runs need to be compared. Covers guardrails, gotchas, and anti-patterns.
author: xizhuomengcontin
version: 1.0.0
---

# orca — run recording and offline replay

You know what a shell command is. This teaches the workflow around one CLI: [OrcaReplay](https://github.com/Continuum-AI-Corp/OrcaReplay), npm package `orcareplay`, command `orca`, Apache-2.0, Node 20+.

`orca` records an agent run at the model-provider boundary — prompts, tool calls, responses, raw bytes — into a local trace, and replays that trace with no provider contacted.

## When to reach for it

- An agent run finished and produced a result nobody can explain.
- A failure needs reproducing, but re-running the agent means paying for the same calls twice.
- Two runs of the same task need comparing (different prompt, different model, different code).

## Command map

| Need | Command | Notes |
|---|---|---|
| Is there a trace? | `orca list` | Newest first; names the run each fork came from. Empty means nothing was recorded |
| What happened | `orca show` | Model turns with token counts and stop reasons, tool calls with arguments and results, shell commands with exit codes, files changed |
| Why it happened | `orca graph --to <seq>` | Only the causal chain to one event. Prefer this over reading a long timeline |
| Fork points | `orca checkpoints` | Choose where a comparison run starts |
| Re-run offline | `orca replay <run>` | Ends with a `reused=n/m` line |
| Compare runs | `orca compare` | Diff two runs, including across models |

Every command defaults to the most recent run. When that is not what the user meant, pass the run explicitly.

## Guardrails

1. **A replay is not a dry run.** The agent process runs again, so every shell command the run issued runs again. List the recorded commands and state the blast radius before starting.
2. **Replay into a scratch worktree.** Otherwise the recorded file tree is restored over the working tree; uncommitted work is absent during the replay and stays absent if it is interrupted.
3. **Quote the `reused=n/m` line verbatim** in whatever you report, and say what it does not prove: a replay shows the recording is self-consistent, not that a fresh run would fail again.

```bash
git worktree add ../replay-scratch HEAD
cd ../replay-scratch
orca replay <run>
```

## Gotchas

- **`reused=3/5` is usually not a partial failure.** Harnesses make calls for themselves — a quota probe, a session-naming request — and a replay does not repeat them. Twenty minutes get spent debugging a non-problem here.
- **An empty trace is not "nothing happened".** It means nothing was captured, usually because the agent pins its own provider origin instead of reading base-URL configuration.
- **Recorded and inferred edges look alike in prose, not in the data.** `orca graph` labels each edge: `recorded` means the recorder watched it happen; `inferred` means it was derived at query time from a named rule the trace does not vouch for. Say which one carries your conclusion.
- **Forks do not inherit later events.** A fork restarts from a checkpoint, so anything the original run did after that point will not appear in the forked trace.

## Error recovery

| Symptom | First move |
|---|---|
| `orca: command not found` | `npm install -g orcareplay`; confirm Node 20+ |
| `orca list` empty | Nothing recorded. Start a recording rather than reconstructing the run |
| Replay stops partway | Read the recorded commands for the failing step; the recording may end mid-command |
| Provider errors during replay | A replay should not reach a provider. Check that the agent under test is not bypassing the base-URL indirection |

## Anti-patterns

- Reconstructing a run from memory or from a chat transcript instead of reading the trace.
- Reading a 200-event timeline and reasoning over it when `orca graph --to <seq>` answers the actual question in one call.
- Replaying in the live working tree to save a `git worktree add`.
- Reporting an inferred edge as an observed fact.

## Boundaries

This is a workflow guide, not a substitute for the upstream documentation. When the CLI behaves differently from this page, the installed version wins — check `orca --help` and the project README before assuming the guide is stale.

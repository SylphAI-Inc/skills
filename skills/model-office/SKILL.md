---
name: model-office
description: Launches "Model Office" — a live browser dashboard that visualizes multi-model job routing as a blocky Lego/Minecraft-style pixel office. Type one task, a dispatcher LLM decomposes it into subtasks and routes each to the best-fit model (Claude/GPT/Sonar) based on capability, and pixel-art worker avatars slide between a "working area" desk and a "waiting area" lounge as their live status changes (queued/thinking/done). Use when the user wants to demo/visualize multi-agent or multi-model job allocation, wants a "pixel agents"-style dashboard, or asks to see how tasks get routed across different models.
author: SylphAI Inc
version: 0.1.0
---

# Model Office

A local FastAPI + WebSocket + HTML5 Canvas demo that visualizes capability-based
job routing across multiple LLMs as a blocky Lego/Minecraft-style office.
Inspired by [pixel-agents-hq/pixel-agents](https://github.com/pixel-agents-hq/pixel-agents),
but built for capability-based multi-model routing rather than parsing a single
coding agent's transcript.

## Architecture

- `scripts/server.py` — FastAPI backend: `POST /api/task` (submit a task),
  `POST /api/events` (producers push status), `GET /ws` (broadcast to
  browser), serves `scripts/frontend/` as static files.
- `scripts/dispatcher.py` — one Claude call decomposes the task into
  2-4 subtasks and assigns each to the worker whose capability best fits
  (`claude` = code/reasoning, `gpt` = writing/general, `sonar` = research
  requiring live web facts). Emits `jobCreated`/`jobAssigned` events.
- `scripts/worker.py` — runs each subtask against its real assigned model
  API, emitting `queued → thinking → done/error` status events as it goes.
  Subtasks for different workers run concurrently.
- `scripts/run.py` — orchestrator: starts the server if not running, opens
  the browser, and (optionally) dispatches a task from argv.
- `scripts/frontend/` — canvas-based **two-zone office UI**: an upper grey
  "WORKING AREA" (desks with monitors) and a lower green "WAITING AREA"
  (lounge benches), separated by a thick red brick divider — Lego/Minecraft
  blocky art style. Worker avatars (`sprites/claude.png`, `sprites/gpt.png`,
  `sprites/sonar.png`) smoothly slide up to their desk when status becomes
  `thinking`, and slide back down to the lounge when `done`/`idle`/`error`.
  Job tickets fly from a queue to the assigned worker's desk; speech bubbles
  show live status text; a log feed sits underneath. Connects via WebSocket,
  replays event history on reconnect.

## When to Use

Activate this skill when the user:
- Wants to see/demo how work routes across multiple models based on capability
- References "pixel agents", "pixel office", "model office", or this skill by name
- Wants a live visual (browser) showing multiple agents/models picking up jobs and their status
- Asks "can you show me job allocation across models visually"

## Prerequisites

Real API keys must be present in the environment before running workers:
- `ANTHROPIC_API_KEY` (dispatcher + claude worker)
- `OPENAI_API_KEY` (gpt worker)
- `PERPLEXITY_API_KEY` (sonar worker, native web search)

If any key is missing, `worker.py` raises an auth error for that worker
only — the other workers still complete. Check with:
```bash
env | grep -E 'ANTHROPIC_API_KEY|OPENAI_API_KEY|PERPLEXITY_API_KEY' | sed 's/=.*/=<set>/'
```
An env var appearing in `env` output with a non-empty value after `=` is
what matters — a bare `KEY=` (empty) still shows the name but has no
value. Verify with `echo "LEN=${#OPENAI_API_KEY}"` (0 means unset/empty).

## How to Run

```bash
cd skills/model-office/scripts
pip install -q -r requirements.txt   # first run only

# Option A: server + browser only, submit tasks from the UI
python3 server.py &
python3 -c "import webbrowser; webbrowser.open('http://127.0.0.1:8787')"

# Option B: one-shot — starts server, opens browser, dispatches a task, prints results
python3 run.py "Plan a 3-day Tokyo trip, write a fun blog intro, and research current visa rules for US citizens."
```

The dashboard also has a text input + Dispatch button, so once the server is
running the user can type new tasks directly in the browser without invoking
`run.py` again — it posts to `/api/task` which runs the dispatcher+workers
in the background and streams status over the existing WebSocket.

If a live agent (e.g. AdaL, Claude Code) is already running and separate API
keys aren't configured for `worker.py`, the agent can relay the pipeline
itself: `POST /api/events` directly with `jobCreated`/`jobAssigned`/
`workerStatus`/`jobDone` events using its own model access (e.g. `consult`,
`web_search`) so the browser still animates a live run.

## Customizing Workers

Capability routing rules live in `dispatcher.py::WORKER_CAPABILITIES` and the
`DECOMPOSE_SYSTEM` prompt. To add/swap a worker:
1. Add its capability description to `WORKER_CAPABILITIES`.
2. Add a `_call_<worker>()` function in `worker.py` and register it in `_CALLERS`.
3. Add an entry to `WORKERS` in `frontend/app.js` with a desk `x` position.
4. Generate a matching pixel-art sprite (16-bit style, magenta background,
   front-facing standing pose) and save to `frontend/sprites/<worker>.png`.

## Known Limitations

- Single-machine demo only — not wired into any specific agent's own
  orchestration; it's a standalone visualization of the *concept* of
  capability-based multi-model routing, using direct API calls to
  Anthropic/OpenAI/Perplexity.
- No persistence — job history resets on server restart or `POST /api/reset`.
- No cost/token tracking per worker yet (a natural next step: add token
  usage + running $ to the `jobDone` event payload and render it under the
  worker's name plate).
- No self-evolving/learned routing yet (a natural next step: a skill-library
  cache mapping job-type signatures to the model+prompt combo that
  succeeded before, with fallback to the LLM dispatcher on cache miss).

---
name: codegraph
description: Turn any codebase into an explorable interactive graph so a developer can understand it fast. Deterministic scan (files, imports, symbols, call edges, PageRank importance, architectural layers, dependency cycles, entry points) plus optional AI enrichment (plain-English summaries and guided tours), delivered as ONE self-contained HTML file. Use when asked to explain, map, visualize, diagram, onboard onto, or understand a repository or its architecture.
author: SylphAI-Inc
version: 1.0.0
---

# codegraph

Turn a codebase into a map a human can actually read.

**The goal is not a graph that shows off how complex the code is — it is a graph that quietly teaches someone how the pieces fit together.**

## When to Use

Trigger on requests like:
- "help me understand this codebase" / "I just joined this project"
- "map / visualize / diagram this repo or its architecture"
- "what are the entry points?" / "how does data flow through this?"
- "generate an onboarding guide" / "where do I start reading?"
- "show me the dependency graph" / "find circular dependencies"
- "which files are most important here?"

Do **not** use this for a single-file explanation — just read the file.

## Core Design (read this before running anything)

Three stages. Two are deterministic; only the middle one uses your intelligence.

```
1. scan.py    codebase  ->  graph.json + digest.md     deterministic, no LLM, no network
2. YOU        digest.md ->  enrich.json                 summaries, layer fixes, tours
3. render.py  both      ->  codegraph.html              one portable self-contained file
              (overview.py collapses the graph into the overview diagram en route)
```

Why this split matters — **do not violate it**:

| Stage | Owner | Guarantee |
|---|---|---|
| Structure (files, imports, calls, metrics, cycles) | `scan.py` | Reproducible. Same commit always yields the same edges. |
| Meaning (what a file is *for*, tours) | You | Only a model can write this. |
| Delivery (layout, validation, HTML) | `render.py` | Validated before write; a broken artifact never replaces a good one. |

**Never hand-write `graph.json`.** It is machine output. You only ever write `enrich.json`.
**Never invent files, symbols, or relationships.** Every id you emit must already exist in the digest.

## Instructions

### Step 1 — Scan (always start here)

```bash
python3 <skill>/scripts/scan.py <repo> -o <repo>/.codegraph
```

Nothing to install: Python 3.8+ stdlib only. ~2s for 230k LOC.

Useful flags:
- `--max-files N` (default 4000) — raise it if output warns about truncation
- `--symbols-for N` (default 250) — extract function/class nodes for the N most important files
- `--no-calls` — skip heuristic cross-file call edges (faster, fewer false positives)

Then **read `digest.md`, not `graph.json`.** The digest is a compact briefing (entry points, directory map, ranked-importance table, cycles, dependencies, layer counts). `graph.json` can be megabytes and will flood your context for no benefit.

### Step 2 — Enrich (this is your real work)

Write `<repo>/.codegraph/enrich.json`:

```json
{
  "project": { "description": "1-3 sentences: what this codebase IS and does." },
  "nodes": {
    "file:src/server.ts": {
      "summary": "HTTP entry point. Wires middleware, mounts routers, starts the listener.",
      "layer": "entry",
      "tags": ["bootstrap", "http"]
    }
  },
  "layers": { "service": "Domain logic; no HTTP or SQL touches this layer." },
  "tours": [
    {
      "title": "Request lifecycle",
      "description": "Follow one HTTP request end to end.",
      "steps": [
        { "nodeId": "file:src/server.ts", "note": "Request arrives; middleware chain runs here." },
        { "nodeId": "file:src/routes/user.ts", "note": "Routing picks a handler." }
      ]
    }
  ]
}
```

Rules:
1. **Node ids must come from the digest verbatim** (`file:...`, `mod:...`, `sym:...`, `ext:...`). Unknown ids are dropped with a warning — silent quality loss.
2. **Summarize the top ~30-60 ranked files first.** Full coverage of a large repo is rarely worth the tokens; importance ordering already tells you what matters.
3. Write **what it is + why it exists**, not a restatement of the filename. Bad: "Utils file with utilities." Good: "Retry/backoff helpers shared by every outbound API client."
4. **Fix wrong layers.** `scan.py` guesses from paths and says so. If `core/` is really data access, override it.
5. **At least one tour, 3-6 steps.** Tours are the single highest-value output for onboarding — they encode reading *order*, which a graph alone cannot.
6. Read actual source before summarizing important files. Do not infer from names alone.

Scale guidance: read the top files in batches, and prefer breadth (many short, correct summaries) over depth (a few essays).

### Step 3 — Render and verify

```bash
python3 <skill>/scripts/render.py --in <repo>/.codegraph --open
```

- Validates first; on failure it prints exact reasons and writes nothing.
- `--validate-only` to check without writing; `--strict` to fail on warnings.
- Output: `<repo>/.codegraph/codegraph.html` — one file, no CDN, works offline, safe to commit or send.

Always report to the user: node/edge counts, how many summaries and tours landed, and the artifact path.

## What the artifact gives the reader

**Three linked views in one file**, cycled with `Tab`:

1. **overview** — architecture diagram (module boxes on layer bands, flowing
   connectors, a comet on the primary dependency path). Answers *"what are the parts?"*
2. **star map** — the same modules as an **orbitable** galaxy field, brightness =
   importance (Physics-atlas idiom: hot cores, double halos, diffraction spikes).
   Answers *"where is the weight of this system?"*
   **Drag to orbit · scroll to dolly · shift-drag to pan · `0` to reset**, with damped
   inertia and a slow idle auto-rotate — the same interaction contract as the atlas'
   `OrbitControls`, implemented as a projected 2.5D disc in Canvas so the artifact
   stays one dependency-free file (no three.js, no WebGL). Touch: one finger orbits,
   two pinch-zoom. Modules carry real `z` depth, so tilting reveals structure and
   distant galaxies fade.
3. **explore** — an **expandable tree**, opened one level at a time. It starts at the
   project root showing only the top folders, and each click reveals the next level:
   folders -> files -> symbols. A `+N` badge on every collapsed node says how much is
   inside, so nothing is hidden silently. The rail's **Start here** list jumps straight
   to a real entry point. `H` toggles back to the flat all-at-once graph.

Clicking a module box or a galaxy drills into explore, focused on that module's files.

### Every node says something (no LLM required)

`scan.py` reads the codebase's **own docstrings and file-header comments** — module
docstrings, JSDoc blocks, Go/Rust line comments — and uses them as node summaries.
Boilerplate (shebangs, licence headers, `coding:` lines) is filtered, and text is cut
at `Args:`/`Returns:` so the summary stays one sentence.

Measured on a real 109k-LOC repo: **87% of files described with zero model calls.**
The agent's `enrich.json` overrides these where it can say something better, and the
inspector labels which is which — an extracted summary is marked *from the file's
docstring*, so provenance is never ambiguous. Nodes also list the symbols they define.

This matters because a graph of unlabelled dots teaches nothing: before this, 100% of
nodes showed only LOC and degree.

The overview is *derived*, never authored: tiers, boxes, link weights and the journey
all come from the deterministic scan, so the diagram cannot drift from the real code.
Modules holding only config/docs are omitted (scaffolding is not architecture), and
links are capped so a dense graph does not become a hairball.

| Capability | Why it helps understanding |
|---|---|
| **Overview diagram** | The 5-second read: what this system is made of, and how it flows |
| **Click a module → explore** | Overview answers "where?", explore answers "how?" |
| 3 detail levels (Folders / Files / Symbols) | Progressive disclosure — start coarse, drill only where needed |
| Layer bands (entry → api → service → data → util) | Shows architecture, not just a hairball |
| Click any node | Summary, metrics, and **navigable** dependency lists both directions |
| Search (`/`) | Find by name, path, summary text, or tag |
| Focus dimming | Isolates one node's actual neighborhood |
| `entries` toggle | "Where do I start reading?" answered instantly |
| `cycles` toggle | Circular dependencies = refactor targets |
| Guided tours (`P`, `[`, `]`) | Teaches reading order — the thing new devs lack most |
| `calls` / `deps` toggles | Cross-file call edges; external dependency surface |
| Theme toggle (`T`), fit (`0`) | Presentable in a README, PR, or onboarding doc |
| **Flowing comet packets** | Dependency *direction* becomes visible motion, not a static arrow |
| **Breathing halos** | Entry points, tour steps, and the selection pulse to draw the eye |
| **Motion toggle** (`space`, ⏸) | Pause for screenshots; auto-off under `prefers-reduced-motion` |
| `Tab` | Flip between overview and explore |
| **`simplify`** (`F`) | Folds edges of hub files — the single biggest declutter (~−48%) |
| **`focus`** (`N`) | Shows only the selection and its top neighbours (~−87%) |

### Asking questions mid-explore

The artifact is offline and carries no API key, so it does not pretend to host a chat.
Instead every node has an **`ask ▸`** button that copies a complete prompt — path,
summary, LOC/fan-in/fan-out, the symbols it defines, and both edge directions — ready
to paste into any LLM. That is the context a model would otherwise have to guess at.

Deliberately NOT done: embedding an API key in the HTML. The file gets committed and
shared, so a key in it is a leak waiting to happen.

### Keeping explore readable

Dense repos produce a hairball, so the explore view **starts simplified** and lets the
reader add detail back:

- **Tests hidden by default** — often half a repo's files, but not its architecture.
- **Hub folding on by default.** A handful of files carry most of the clutter (in one
  109k-LOC repo, 10 files owned 23% of all edge endpoints). Their edges collapse to a
  `⋯n` badge; click it to reveal them. Nothing disappears silently.
- **`calls` edges off by default** — they typically outnumber imports ~5:1.
- **Distance LOD** — zoomed far out the lines fade and the layer bands carry the
  structure (borrowed from Physics-atlas's `uReveal`).
- **Neighbourhood focus** (`N`) — one node's direct relations only, capped so an
  extreme hub cannot re-create the hairball.

Measured on a 109k-LOC repo: **628 → 172 edges (−73%)** at defaults, **−87%** in focus mode.

**Why not 3D?** It looks like the answer but is not: the clutter is edge *count*, not
missing dimension, and 3D adds occlusion, rotation disorientation, and a ~600KB
three.js dependency that breaks the single-file offline contract. LOD plus folding
solves the actual problem.

### Animation

The artifact is alive by default, in the glowmotion/deep-field idiom:

- **Comet packets** travel source → target along each edge with an exponential
  fading trail, so import direction reads at a glance. Colour encodes kind
  (blue = imports, violet = calls, gold = the active tour path).
- **Focus redirects traffic**: selecting a node concentrates packets on its
  neighbourhood and fades the rest to 6%.
- **Breathing halos** ring entry points, tour steps, and the selection.
- **Parallax starfield** drifts behind the graph as you pan (dark theme only;
  the light theme stays print-clean).

Performance is decoupled from graph size: the static scene is painted once on a
base canvas and motion lives on a separate overlay, with packets capped at 190.
Measured **60fps on a 2,660-node graph**. Motion pauses on `space` / ⏸ and is
off automatically when the viewer prefers reduced motion.

## Graph Vocabulary

**Node ids are typed prefixes** (stable, so deep links and enrichment keep working):

| Prefix | Meaning |
|---|---|
| `mod:<dir>` | Folder / module |
| `file:<path>` | A file |
| `sym:<path>#<name>:<line>` | Function / class / type |
| `ext:<name>` | External dependency |

**Edges**: `contains` (hierarchy), `imports` (resolved, reliable), `calls` (heuristic — name-based, unique-match only), `depends_on` (external), `inherits`.

**Layers**: `entry`, `ui`, `api`, `service`, `data`, `util`, `config`, `infra`, `test`, `docs`, `other`.

**Importance** = 0.55·PageRank(imports) + 0.25·fan-in + 0.20·size. It answers "what should I read first?"

## Languages

Python, JS/TS (+JSX/TSX), Vue, Svelte, Go, Rust, Java, Kotlin, Scala, Ruby, PHP, C#, C/C++, Objective-C, Swift, shell, SQL, Terraform, GraphQL, Protobuf — plus config/docs/Docker as context nodes.

Import resolution is real (relative paths, package roots, `@/` aliases, Go modules, Rust `crate::`/`mod`, JVM packages). Extraction is regex-based, not a full type-checking AST: excellent for imports and definitions, approximate for call edges. **Tell the user this when they ask about call accuracy** — never present inferred calls as verified fact.

## Honest Limits

- `calls` edges are heuristic (unique unambiguous names only; common names like `get`/`run` are deliberately skipped). Imports are trustworthy; calls are a hint.
- Dynamic imports, DI containers, reflection, and runtime registration are invisible to static scanning.
- Generated code, minified bundles, and lockfiles are excluded on purpose.
- Layers are path heuristics until you override them. Say so rather than overclaiming.

## Refresh

Re-run `scan.py` then `render.py`. `enrich.json` is separate from `graph.json`, so **existing summaries survive a re-scan** — only ids that no longer exist get dropped. Commit `.codegraph/` to let teammates open the graph with zero setup and no API key.

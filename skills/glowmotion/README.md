# Glowmotion

**Premium animated technical diagrams as single self-contained HTML files.**

Flowcharts whose connectors visibly flow. Architecture diagrams where requests
travel as glowing comet dots with fading trails. Pulsing module halos, icon
glyphs, a title capsule — and a built-in ☀/☾ light/dark toggle. All of it is
vector SVG + CSS + SMIL, so a diagram is tens of KB, scales losslessly, respects
`prefers-reduced-motion`, and opens in any browser straight from the filesystem.

No build step, no npm install, no external assets. **Requires `python3` only**
(pure stdlib).

> This README is the human-facing overview. The agent-facing instructions live
> in [`SKILL.md`](./SKILL.md); the full authoring contract is in
> [`references/graph-format.md`](./references/graph-format.md).

---

## Why it exists

Most diagram tooling forces a trade: either you hand-place every box (slow, and
it rots the moment the design changes), or you accept a generic auto-layout that
looks like generated output. Glowmotion splits the problem in two:

- **You author semantics** — nodes, edges, groups, the animated request paths,
  and the copy. A small JSON file.
- **The engine owns geometry** — layering, row packing, boundary padding,
  orthogonal collision-safe routing, both theme palettes, and the whole
  animation layer.

Because the layout is deterministic, it is also *checkable*. Glowmotion ships a
mechanized verifier that catches overlaps, connectors crossing boxes, dots
drifting off their path, and a missing animation layer — the class of defect
that is invisible when you eyeball the code and embarrassing when someone else
opens the file.

---

## When to use it

Reach for Glowmotion whenever the subject **moves**: requests, events, data,
jobs, messages, control flow.

| You want | Mode |
|---|---|
| Steps, sequence, branching, state transitions — *"what happens, in what order"* | `flow` |
| Components, services, containment, topology — *"what the system is made of"* | `architecture` |

Mixed request → `architecture`; the animated journey *is* the flow.

Good fits: landing-page hero diagrams, README architecture sections, docs
pipelines, product demos, conference slides, X/LinkedIn posts.

It also **converts Mermaid source** (`flowchart`/`graph` and
`stateDiagram-v2`), preserving every label verbatim and verifying fidelity
against the original.

---

## Install

Glowmotion ships in the `core-skills` plugin of the
[AdaL Skills Marketplace](../../README.md). Both AdaL CLI and Claude Code use
the same commands:

```
/plugin marketplace add SylphAI-Inc/skills
/plugin install core-skills@adal-agent-skills
```

Then just ask, in natural language:

> "Draw me an animated architecture diagram of this repo's request path, neon theme."

The skill triggers on its own — you never invoke the scripts by hand in normal
use. Everything below is for people who want to understand or extend the engine.

---

## How it works

```
  your graph.json  ──▶  layout.py --render  ──▶  diagram.html
  (semantics, copy)      (all geometry,           (self-contained,
                          both palettes,          ~20 KB)
                          animation layer)
                                │
                                ▼
                    check_diagram.py   (geometry: C1–C10)
                    check_fidelity.py  (Mermaid input only)
                                │
                                ▼
                        0 violations → ship
```

### 1. Author the graph

A semantic graph, written to a **temp path** (it is a throwaway intermediate,
not a deliverable):

```json
{
  "mode": "architecture",
  "darkTheme": "midnight",
  "title": "Request path",
  "titleHighlight": "end to end",
  "subtitle": "Edge cache absorbs reads; writes fan out through the bus.",
  "nodes": [
    {"id": "web",   "label": "Web client",  "type": "frontend"},
    {"id": "api",   "label": "API gateway", "type": "backend"},
    {"id": "cache", "label": "Redis",       "type": "database", "sublabel": "read-through"},
    {"id": "db",    "label": "Postgres",    "type": "database"}
  ],
  "edges": [
    {"from": "web",   "to": "api",   "kind": "main", "label": "HTTPS"},
    {"from": "api",   "to": "cache", "kind": "sync"},
    {"from": "cache", "to": "db",    "kind": "async", "label": "miss"}
  ],
  "journeys": [
    {"hops": [["web", "api"], ["api", "cache"], ["cache", "db"]]}
  ],
  "summary": [
    {"accent": "cyan",   "title": "Ingress",  "items": ["TLS terminates at the edge"]},
    {"accent": "violet", "title": "Cache",    "items": ["Read-through, 60s TTL"]},
    {"accent": "rose",   "title": "Storage",  "items": ["Primary + async replica"]}
  ]
}
```

**Journeys are the point.** Each one becomes a glowing dot with two fading
trail dots riding the exact connector path, and every node it touches gets a
pulsing halo on a staggered delay. A diagram with zero journeys fails the
checker — the animation is the deliverable, not decoration.

### 2. Render

```bash
python3 scripts/layout.py graph.json --render request-path.html
```

That single command emits the complete deliverable: every coordinate and path,
both theme palettes plus the ☀/☾ toggle, the glow/trail/halo animation layer,
icons, legend, summary cards, the ⏯ pause button, reduced-motion handling, and
ARIA wiring.

Omit `--render` and it prints the computed geometry as JSON instead — useful for
inspecting layout decisions.

### 3. Verify (non-negotiable)

```bash
python3 scripts/check_diagram.py request-path.html
```

It must print `0 violations`. Never verify by eyeballing the code or opening a
browser — label drift and geometry errors are invisible to the eye.

| Checker | Catches |
|---|---|
| `check_diagram.py` | partial overlaps (C1), connectors through boxes (C2), dash-loop seams (C3), out-of-viewBox (C4), dots off their line (C5), black-fill paths (C6), endpoint pierce (C7), dangling SMIL refs (C8), foreign node inside a group (C9), missing/overstuffed animation layer (C10) |
| `check_fidelity.py` | Mermaid input only: node/edge/label drift vs. the source `.mmd` |

For Mermaid input, also run the fidelity check until it reports `PASS`:

```bash
python3 scripts/check_fidelity.py source.mmd request-path.html
```

Fix violations by editing the JSON and re-rendering — cheap and deterministic.
For a colliding label: shorten it, move it to a different edge, fold it into the
node as a `sublabel`, or drop it when the edge reads fine without one.

---

## Themes

Every file ships **both** a dark and a light palette with a toggle button, and
opens following the viewer's OS `prefers-color-scheme`.

| Theme | Slot | Canvas | Vibe |
|---|---|---|---|
| `midnight` *(default dark)* | dark | deep navy `#020617` | emerald flow, cyan dots — clean docs look |
| `neon` | dark | pure black `#000` | green/purple/cyan/amber, high drama |
| `aurora` | dark | deep slate `#030712` | teal/violet borealis |
| `daylight` *(default light)* | light | soft blue-grey `#e8eef5` | saturated strokes, print-friendly |

Pick by context: `neon` for landing-page drama, `midnight` for docs, `aurora`
for data/ML topics.

Control keys: `darkTheme`, `lightTheme`, `defaultMode`
(`auto` | `dark` | `light`), and `themeToggle: false` to bake one fixed palette
with no button.

---

## Video export

For a GIF or MP4, screen-record the open file, or go headless:

```bash
npx --yes timecut diagram.html --viewport=1200,900 --duration=3 --fps=30 --output=out.mp4
ffmpeg -i out.mp4 out.gif
```

A 3s capture loops seamlessly when all durations divide 3s. Never render frames
by hand.

If the diagram is bound for a phone feed, remember that the aspect ratio is
decided by the graph, not the encoder: X caps media at 9:16, and a tall
top-down flow gets thumbnailed into illegibility. Condense the graph — merge
detail nodes into the node that carries the story — rather than shrinking the
font. Prefer MP4 over GIF: far smaller and sharper text.

---

## Output contract

One self-contained `.html`:

- Embedded CSS, inline SVG, **no external assets**
- No JS dependencies beyond a ~25-line inline theme/pause/reduced-motion script
- Renders correctly opened from the filesystem (`file://`)
- Light or dark per the viewer's preference, or pinned via `defaultMode`
- Accessible: ARIA title/desc wiring, honors `prefers-reduced-motion`

---

## Repository layout

```text
glowmotion/
├── SKILL.md                       # agent instructions (the entry point)
├── README.md                      # this file
├── references/
│   └── graph-format.md            # full graph JSON contract + theme table
└── scripts/
    ├── layout.py                  # geometry engine + HTML renderer
    ├── check_diagram.py           # geometry checks (C1–C10)
    └── check_fidelity.py          # Mermaid fidelity check
```

`layout.py` is intentionally a black box — `references/graph-format.md` is the
complete contract. If something is unclear, run it on a tiny graph and look at
the output.

---

## License

MIT, as part of the [AdaL Skills Marketplace](../../README.md).

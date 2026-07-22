---
name: glowmotion
description: 'Create premium animated technical diagrams as single self-contained HTML+SVG files — flowcharts whose connectors visibly flow and architecture diagrams where requests travel as glowing comet dots with fading trails, pulsing module highlights, and a built-in light/dark theme toggle (dark themes midnight/neon/aurora + light theme daylight). Use this skill whenever the user asks for a flowchart, workflow, pipeline, process diagram, state machine, system architecture, infrastructure, cloud, microservices, or network topology diagram — especially when they mention "animated", "glowing", "premium", "flowing", "dynamic", "alive", "GIF-like", "light mode", "dark mode", or want a diagram for a landing page, README, docs, or product demo. Also converts Mermaid source (flowchart/graph and stateDiagram-v2) into an animated diagram. Prefer this over static output whenever the diagram represents anything that moves: requests, events, data, jobs, messages, or control flow.'
author: Aria068
version: 0.2.0
---

# Glowmotion

Create premium animated technical diagrams as single self-contained HTML files.
Glowmotion combines a deterministic layout engine (dashmotion lineage: the
script computes every coordinate and route, mechanized checkers verify the
result) with a lanshu-style premium finish (glow-trail dots, pulsing module
halos, grain + vignette, icon glyphs, title capsule) — implemented entirely as
vector SVG/CSS/SMIL, so the output stays a few KB, scales losslessly, respects
reduced motion, and opens in any browser straight from the filesystem.

**Requires `python3`** (pure stdlib — no pip installs). There is no hand-layout
fallback: the engine owns all geometry.

## Step 1 — Pick the mode and theme

| User wants | Mode |
|---|---|
| Steps, sequence, branching, state transitions ("what happens, in what order") | **flow** |
| Components, services, containment, topology ("what the system is made of") | **architecture** |

Mixed request → architecture; the animated journey *is* the flow.

**Themes are light/dark switchable by default.** Every generated file ships
*both* a dark and a light palette and a **☀/☾ toggle button** (top-right, next
to pause); it opens following the viewer's OS `prefers-color-scheme`. You choose
which two palettes pair up:

- `darkTheme` (default **midnight**) — dark options: **midnight** (deep navy,
  emerald flow), **neon** (pure-black canvas, green/purple/cyan/amber),
  **aurora** (teal/violet on deep slate).
- `lightTheme` (default **daylight**) — light options: **daylight** (soft
  blue-grey paper, saturated strokes, print-friendly). *(only light theme today)*
- `defaultMode`: `"auto"` (default, follow OS) | `"dark"` | `"light"` — which
  side the file opens on. Set `"light"` when the user asks for a light diagram.
- `themeToggle: false` — bake a single fixed theme (from `theme`/`darkTheme`),
  no button. Only when the user explicitly wants one locked look.

Legacy `theme` (single key) still works: a light value fills the light slot, a
dark value the dark slot, the other slot takes its default — still switchable.
Pick dark palettes by context: neon for landing-page drama, midnight for docs,
aurora for data/ML topics.

**Mermaid input** — if the request contains Mermaid source (```mermaid block,
`.mmd` file, or pasted code): supported types are `flowchart`/`graph` and
`stateDiagram-v2`; say so and offer alternatives for others. Keep every node,
edge, group, and legend label **verbatim** — never reword, merge, or add
punctuation; Step 3's fidelity check compares exactly. Layout is always
recomputed top-down regardless of the source's declared direction.

## Step 2 — Author the graph, render the file

You author a *semantic* graph JSON — structure, types, journeys, copy — and the
engine does everything else. Full contract in `references/graph-format.md`
(read it before your first graph in a session). The essentials:

1. Parse the request (or the Mermaid source) into the graph JSON: nodes
   (`type` for arch, `shape` only for flow pills/decisions, `tier` only for
   multi-group arch), edges (`kind`: sync/async/main/static), groups, 1–4
   `journeys` (the animated request paths — **always author at least one**;
   the checker fails a diagram with no traveling dot), and the copy: `title`,
   `titleHighlight` (capsule phrase), `subtitle`, arch `summary` of exactly
   three cards, optional `signature`.
2. Write the JSON to a **temp path** (`mktemp`/`$TMPDIR`), never the output
   folder — it is a throwaway intermediate.
3. Render: `python3 <skill-dir>/scripts/layout.py graph.json --render
   <topic>-glowmotion.html`. The output is the complete deliverable: geometry,
   both theme palettes + ☀/☾ toggle, glow/trail/halo animation layer, icons,
   legend, cards, pause toggle, reduced-motion handling, ARIA wiring.

To change anything, edit the JSON and re-render (cheap, deterministic); for a
one-off wording tweak, edit the emitted HTML directly. Never hand-compute
coordinates and never write the HTML from scratch.

## Step 3 — Verify before delivering (non-negotiable)

The file is done when the checkers say so — **never** verify by eyeballing the
code or opening a browser/screenshot; label drift and geometry errors are
invisible to the eye.

```bash
python3 <skill-dir>/scripts/check_diagram.py <your-file>.html
```

Detects: partial overlaps (C1), connectors through boxes (C2), dash-loop seams
(C3), out-of-viewBox (C4), dots off their line (C5), black-fill paths (C6),
endpoint pierce (C7), dangling SMIL begin refs (C8), foreign node inside a
group box (C9), and a missing/overstuffed animation layer (C10). Fix every
violation and re-run until it prints `0 violations` — usually by editing the
graph JSON and re-rendering.

**If the input was Mermaid**, also run the fidelity check and fix to `PASS`:

```bash
python3 <skill-dir>/scripts/check_fidelity.py <source>.mmd <your-file>.html
```

Deliver only after a clean pass. Tell the user the file opens directly in any
browser, has a ☀/☾ light-dark toggle and a ⏯ pause button, and honors
reduced-motion preferences.

### GIF/MP4 export (only if asked)

Never render frames by hand. Screen-record the open file, or headless:
`npx timecut <file.html> --viewport=1200,900 --duration=3 --fps=30
--output=out.mp4` then `ffmpeg -i out.mp4 out.gif`. A 3s capture loops
seamlessly when all durations divide 3s.

## Output contract

One self-contained `.html`: embedded CSS, inline SVG, no external assets, no
JS dependencies beyond the ~25-line inline theme/pause/reduced-motion script.
Renders correctly opened from the filesystem, in light or dark per the viewer's
preference (or the pinned `defaultMode`).

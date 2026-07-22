#!/usr/bin/env python3
"""layout.py — deterministic layout + premium render engine for glowmotion.

glowmotion combines two lineages:
  * the dashmotion layout engine (deterministic geometry: longest-path
    layering, row packing, boundary padding, C2-safe orthogonal rail/lane
    routing, pure stdlib, verified by check_diagram.py), and
  * the lanshu aesthetic (glow-trail dots, pulsing module highlights, film
    grain + vignette finish, icon glyphs, title highlight capsule, signature
    slot) — reimplemented as vector SVG/CSS/SMIL so the output stays ONE
    self-contained HTML file, a few KB, accessible, and pausable.

The model authors a *semantic* graph JSON (nodes/types/edges/groups/journeys
+ theme + copy); this script does all placement arithmetic AND writes the
complete, ready-to-ship HTML. The model never computes a coordinate.

  python3 layout.py graph.json                     # geometry JSON -> stdout
  python3 layout.py graph.json --render out.html   # finished, ready-to-ship HTML

Themes (graph "theme" key): midnight (dashmotion classic blues/greens on deep
navy), neon (lanshu black-canvas green/purple/cyan/amber), aurora (teal/violet
on deep slate). Unknown theme -> midnight + a stderr notice (fail-safe).

Design decisions inherited from dashmotion (frozen, not re-invented here):
  * Shared layered engine. Both modes lay out top-down by layer. Flow computes
    layers by longest-path on the forward DAG (back edges found by DFS); arch
    uses the model-supplied `tier`.
  * C2-safe routing. Adjacent-layer edges use orthogonal L routes whose
    horizontal rail sits in the inter-layer gap (no box there). Edges that span
    >1 layer, or run sideways/upward, route through a vertical lane placed
    OUTSIDE every box (margins) — the lane can never cross a node.
  * Loops render as a `↻ <label>` annotation beside the source, never a drawn
    return path. The label is its own <text> so it survives verbatim.
  * Boundaries: bottom-up member bbox + padding; full containment is legal
    (C1 only flags partial overlap).
  * Positivity: layout runs in arbitrary coordinates, then one translate pass
    shifts everything >=0 and sets viewBox 0 0 W H (C4).

glowmotion additions (all vector, all inside the one output file):
  * Traveling dots get a Gaussian glow (filter #glow) and two fading trail
    dots riding the same path 0.09s/0.18s behind — the lanshu comet look.
  * Nodes touched by a journey get a `halo` rect (identical geometry to the
    node rect, so the checker's dedupe keeps C1 clean) whose stroke pulses on
    a staggered CSS delay — the lanshu module-highlight cycle.
  * Optional film grain (feTurbulence) + vignette (radialGradient) full-bleed
    rects; check_diagram treats ~full-viewBox rects as scenery.
  * Arch node types carry a small <use> icon glyph (defs <symbol>, so the
    checkers never mistake icon strokes for connectors).
  * Title highlight capsule + optional @signature in the header (HTML layer).

Known limitations (documented, NOT worked around by loosening the checker):
  * Within-layer ordering is group-contiguous + input order (no barycenter
    sweep). Wide fan structures may cross visually; never through a box.
  * Layers are centered, not barycenter-aligned to parents.
  * A subgroup is assumed to own its tiers; the graph JSON is authored that way.
  * Curves are not produced; all routing is orthogonal.
"""

import json
import re
import sys

# ----------------------------------------------------------------------------
# constants
# ----------------------------------------------------------------------------

CENTER = 520.0          # provisional spine x; normalized away at the end
MARGIN = 34.0           # outer padding after translate
BOTTOM_PAD = 44.0       # extra below lowest element (SKILL: H = lowest + ~50)

# flow (geometry)
STEP_H = 44.0
PILL_H = 40.0
FLOW_VGAP = 56.0        # node bottom -> next node top
FLOW_HGAP = 30.0
FLOW_MAXW = 190.0

# arch (geometry)
COMP_H = 56.0
BUS_H = 36.0
ARCH_VGAP = 56.0
ARCH_HGAP = 40.0
ARCH_MAXW = 200.0
BOUND_PAD = 20.0

# ----------------------------------------------------------------------------
# themes — every color the renderer uses lives here; geometry never changes.
# type_style: type -> (fill, stroke, legend label)
# accents: journey-dot color cycle (a journey without an explicit color takes
# accents[i % len]); also colors the three summary-card dots.
# ----------------------------------------------------------------------------

THEMES = {
    "midnight": {  # dashmotion classic — deep navy, emerald flow, cyan dots
        "bg": "#020617", "grid": "#0f1b33", "card_bg": "#030a1c",
        "border": "#1e293b", "border_hi": "#334155",
        "text": "#e2e8f0", "subtext": "#64748b", "legend_text": "#94a3b8",
        "footer": "#475569",
        "flow_node_fill": "rgba(16,185,129,0.04)", "flow_node_stroke": "#10b981",
        "flow_pill_fill": "rgba(52,211,153,0.06)", "flow_pill_stroke": "#34d399",
        "flow_conn": "#10b981", "flow_dot": "#34d399",
        "arch_conn": "#64748b", "arch_async": "#fb923c", "arch_auth": "#fb7185",
        "arch_dot": "#22d3ee",
        "node_base": "#0b1226",
        "region": "#fbbf24", "subnet": "#fb7185",
        "capsule_fill": "rgba(16,185,129,0.16)", "capsule_text": "#34d399",
        "accents": ["#22d3ee", "#a78bfa", "#fb7185", "#34d399"],
        "type_style": {
            "frontend": ("rgba(8,51,68,0.45)", "#22d3ee", "frontend"),
            "backend":  ("rgba(6,78,59,0.45)", "#34d399", "service"),
            "database": ("rgba(76,29,149,0.45)", "#a78bfa", "data"),
            "cloud":    ("rgba(120,53,15,0.35)", "#fbbf24", "cloud infra"),
            "security": ("rgba(136,19,55,0.45)", "#fb7185", "security"),
            "bus":      ("rgba(154,52,18,0.35)", "#fb923c", "message bus"),
            "external": ("rgba(30,41,59,0.5)", "#94a3b8", "external"),
        },
        "grain": False, "vignette": False,
    },
    "neon": {  # lanshu — pure black canvas, green/purple/cyan/amber/pink
        "bg": "#000000", "grid": "#101210", "card_bg": "#040404",
        "border": "#2a2f31", "border_hi": "#5c6265",
        "text": "#f4f0ee", "subtext": "#8a8482", "legend_text": "#cfc7c5",
        "footer": "#5c6265",
        "flow_node_fill": "rgba(34,200,111,0.05)", "flow_node_stroke": "#22c86f",
        "flow_pill_fill": "rgba(34,200,111,0.09)", "flow_pill_stroke": "#22c86f",
        "flow_conn": "#22c86f", "flow_dot": "#22c86f",
        "arch_conn": "#cfc7c5", "arch_async": "#f4b64e", "arch_auth": "#ff7ab6",
        "arch_dot": "#7ee3d6",
        "node_base": "#060606",
        "region": "#f4b64e", "subnet": "#ff7ab6",
        "capsule_fill": "#124238", "capsule_text": "#22c86f",
        "accents": ["#22c86f", "#bd54d3", "#7ee3d6", "#f4b64e"],
        "type_style": {
            "frontend": ("#04171e", "#7ee3d6", "frontend"),
            "backend":  ("#02160a", "#22c86f", "service"),
            "database": ("#120814", "#bd54d3", "data"),
            "cloud":    ("#1c1204", "#f4b64e", "cloud infra"),
            "security": ("#1c0812", "#ff7ab6", "security"),
            "bus":      ("#1c1204", "#f4b64e", "message bus"),
            "external": ("#0d0d0d", "#cfc7c5", "external"),
        },
        "grain": True, "vignette": True,
    },
    "aurora": {  # teal/violet borealis on deep slate
        "bg": "#030712", "grid": "#0d1526", "card_bg": "#050b18",
        "border": "#1b2740", "border_hi": "#2c3d5f",
        "text": "#e6edf6", "subtext": "#5f7290", "legend_text": "#8fa3c0",
        "footer": "#43536e",
        "flow_node_fill": "rgba(56,189,248,0.05)", "flow_node_stroke": "#38bdf8",
        "flow_pill_fill": "rgba(45,212,191,0.08)", "flow_pill_stroke": "#2dd4bf",
        "flow_conn": "#38bdf8", "flow_dot": "#2dd4bf",
        "arch_conn": "#5f7290", "arch_async": "#fbbf24", "arch_auth": "#f472b6",
        "arch_dot": "#2dd4bf",
        "node_base": "#0a1120",
        "region": "#fbbf24", "subnet": "#f472b6",
        "capsule_fill": "rgba(45,212,191,0.14)", "capsule_text": "#2dd4bf",
        "accents": ["#2dd4bf", "#c084fc", "#f472b6", "#38bdf8"],
        "type_style": {
            "frontend": ("rgba(13,64,80,0.45)", "#2dd4bf", "frontend"),
            "backend":  ("rgba(12,56,90,0.45)", "#38bdf8", "service"),
            "database": ("rgba(70,32,110,0.45)", "#c084fc", "data"),
            "cloud":    ("rgba(110,70,14,0.35)", "#fbbf24", "cloud infra"),
            "security": ("rgba(120,26,70,0.40)", "#f472b6", "security"),
            "bus":      ("rgba(110,70,14,0.35)", "#fbbf24", "message bus"),
            "external": ("rgba(35,46,66,0.5)", "#8fa3c0", "external"),
        },
        "grain": False, "vignette": True,
    },
    "daylight": {  # light — soft blue-grey paper, saturated 600-weight strokes
        "is_light": True,
        "bg": "#e8eef5", "grid": "#d3dded", "card_bg": "#f8fafc",
        "border": "#cbd5e1", "border_hi": "#94a3b8",
        "text": "#0f172a", "subtext": "#64748b", "legend_text": "#475569",
        "footer": "#94a3b8",
        "flow_node_fill": "rgba(5,150,105,0.08)", "flow_node_stroke": "#059669",
        "flow_pill_fill": "rgba(4,120,87,0.12)", "flow_pill_stroke": "#047857",
        "flow_conn": "#059669", "flow_dot": "#059669",
        "arch_conn": "#64748b", "arch_async": "#ea580c", "arch_auth": "#e11d48",
        "arch_dot": "#0891b2",
        "node_base": "#ffffff",
        "region": "#d97706", "subnet": "#e11d48",
        "capsule_fill": "rgba(8,145,178,0.12)", "capsule_text": "#0e7490",
        "accents": ["#0891b2", "#7c3aed", "#e11d48", "#059669"],
        "type_style": {
            "frontend": ("rgba(8,145,178,0.10)", "#0891b2", "frontend"),
            "backend":  ("rgba(5,150,105,0.10)", "#059669", "service"),
            "database": ("rgba(124,58,237,0.10)", "#7c3aed", "data"),
            "cloud":    ("rgba(217,119,6,0.10)", "#d97706", "cloud infra"),
            "security": ("rgba(225,29,72,0.10)", "#e11d48", "security"),
            "bus":      ("rgba(234,88,12,0.10)", "#ea580c", "message bus"),
            "external": ("rgba(100,116,139,0.10)", "#64748b", "external"),
        },
        "grain": False, "vignette": False,
    },
}
DEFAULT_THEME = "midnight"

# lanes
LANE_GAP = 30.0         # first lane this far outside content
LANE_STEP = 16.0        # spacing between stacked lanes
RAIL_IN = 24.0          # rail offset into the inter-layer gap

EDGE_SHORT = 4.0        # connector stops this far short of the target border

# journey dots
DOT_SPEED = 150.0       # px/s travel along a hop
DOT_DUR_MIN = 0.6
DOT_DUR_MAX = 4.0       # cap: a dot on a long cross-diagram edge speeds up
                        # instead of crawling (an 1740px hop was 11.6s -> 4s)


# ----------------------------------------------------------------------------
# text
# ----------------------------------------------------------------------------

def char_w(c):
    o = ord(c)
    if o >= 0x2E80:            # CJK / wide
        return 14.0
    if c in "iljt.,:;'|! ":
        return 5.0
    if c in "mwMW":
        return 11.0
    return 8.0


def text_w(s):
    return sum(char_w(c) for c in s)


def wrap(label, maxw):
    """Wrap to at most two lines; width keyed off the longest line."""
    if text_w(label) <= maxw:
        return [label]
    words = label.split(" ")
    if len(words) > 1:
        best, line1 = None, ""
        for i in range(1, len(words)):
            a = " ".join(words[:i])
            b = " ".join(words[i:])
            score = max(text_w(a), text_w(b))
            if best is None or score < best:
                best, line1, line2 = score, a, b
        return [line1, line2]
    # single long token (e.g. CJK run): split near the middle
    n = len(label)
    cut = n // 2
    return [label[:cut], label[cut:]]


def esc(s):
    # Attribute-safe: this output lands in both text content AND attribute values
    # (data-grp, data-grp-id, title/desc). Quotes MUST be escaped or one " in a
    # label breaks the attribute and corrupts the SVG (it won't even parse as XML).
    # &quot;/&#39; render identically to "/' as text, so escaping them everywhere
    # is lossless. check_fidelity html.unescape()s before comparing, so verbatim.
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


# Style-token guards. The model supplies a few raw style strings — journey dot
# color, retained classDef stroke/dash — that land in SVG *attributes*. Escaping
# isn't enough: a malformed value would render as a broken (or injected)
# attribute, so these validate-or-fall-back. An unrecognized token reverts to the
# engine default and records a one-line notice (surfaced on stderr); they NEVER
# drop a node or abort the render. fail-safe-to-render.
_COLOR_RE = re.compile(
    r'^(?:#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})'
    r'|rgba?\(\s*[\d.]+%?\s*,\s*[\d.]+%?\s*,\s*[\d.]+%?\s*'
    r'(?:,\s*[\d.]+%?\s*)?\))$')
# stroke-dasharray: numbers separated by spaces and/or commas (e.g. "4 3", "2,4")
_DASH_RE = re.compile(r'^[\d.]+(?:[\s,]+[\d.]+)*$')


def safe_color(val, default, what, warnings):
    if not val:
        return default
    s = str(val).strip()
    if _COLOR_RE.match(s):
        return s
    warnings.append(f"{what}: ignored invalid color {val!r}; using {default}")
    return default


def safe_dash(val, what, warnings):
    if not val:
        return None
    s = str(val).strip()
    if _DASH_RE.match(s):
        return s
    warnings.append(f"{what}: ignored invalid stroke-dasharray {val!r}")
    return None


# ----------------------------------------------------------------------------
# model
# ----------------------------------------------------------------------------

class Node:
    def __init__(self, d):
        self.id = d["id"]
        self.label = d.get("label", d["id"])
        self.sublabel = d.get("sublabel")
        self.shape = d.get("shape")          # flow: pill|step|decision
        self.type = d.get("type")            # arch: frontend|...
        self.tier = d.get("tier")
        self.group = d.get("group")
        self.sem_stroke = d.get("semStroke")  # semantic classDef retention
        self.sem_dash = d.get("semDash")
        self.loop_notes = []                 # ↻ annotations attached here
        self.layer = 0
        self.x = self.y = 0.0
        self.w = self.h = 0.0
        self.lines = [self.label]

    @property
    def cx(self):
        return self.x + self.w / 2.0

    @property
    def cy(self):
        return self.y + self.h / 2.0

    @property
    def x2(self):
        return self.x + self.w

    @property
    def y2(self):
        return self.y + self.h


class Edge:
    def __init__(self, d):
        self.src = d["from"]
        self.dst = d["to"]
        self.kind = d.get("kind", "sync")
        self.label = d.get("label")
        self.pts = []                        # orthogonal polyline
        self.is_loop = False
        self.label_pos = None


class Group:
    def __init__(self, d):
        self.id = d["id"]
        self.label = d.get("label", d["id"])
        self.kind = d.get("kind", "region")  # region|subnet
        self.parent = d.get("parent")
        self.box = None                      # (x, y, w, h)


# ----------------------------------------------------------------------------
# layering
# ----------------------------------------------------------------------------

def find_back_edges(node_ids, edges):
    """Iterative colored DFS (no recursion limit games on deep chains)."""
    adj = {n: [] for n in node_ids}
    for i, e in enumerate(edges):
        if e.src in adj:
            adj[e.src].append((e.dst, i))
    color = {}
    back = set()
    for start in node_ids:
        if color.get(start, 0) != 0:
            continue
        stack = [(start, iter(adj[start]))]
        color[start] = 1
        while stack:
            u, it = stack[-1]
            advanced = False
            for v, i in it:
                if v == u:
                    back.add(i)
                    continue
                c = color.get(v, 0)
                if c == 1:
                    back.add(i)
                elif c == 0:
                    color[v] = 1
                    stack.append((v, iter(adj[v])))
                    advanced = True
                    break
            if not advanced:
                color[u] = 2
                stack.pop()
    return back


def longest_path_layers(node_ids, fwd):
    succ = {n: [] for n in node_ids}
    indeg = {n: 0 for n in node_ids}
    for e in fwd:
        succ[e.src].append(e.dst)
        indeg[e.dst] += 1
    level = {n: 0 for n in node_ids}
    queue = [n for n in node_ids if indeg[n] == 0]
    qi = 0
    while qi < len(queue):
        u = queue[qi]
        qi += 1
        for v in succ[u]:
            if level[u] + 1 > level[v]:
                level[v] = level[u] + 1
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    return level


# ----------------------------------------------------------------------------
# input sanity
# ----------------------------------------------------------------------------

def validate_graph(graph):
    """Pre-render sanity on the raw semantic graph. Returns a list of human-
    readable errors (empty == OK), reporting every problem at once.

    The high-value check is the group parent-chain CYCLE: without it a malformed
    parent loop makes the layout engine spin forever (a silent hang that eats the
    latency budget — worse than a crash). The rest turn would-be deep-in-the-
    engine KeyErrors into one clear, up-front report. This is fail-closed by
    design (a structural malformation can't be rendered faithfully) — distinct
    from the fail-safe-to-render style-token guards. Deliberately NOT a general
    JSON-schema validator: it checks only the invariants the engine assumes."""
    nodes = graph.get("nodes")
    if not nodes:
        return ["graph has no 'nodes'"]
    errors = []
    node_ids = set()
    for i, d in enumerate(nodes):
        nid = d.get("id") if isinstance(d, dict) else None
        if nid is None:
            errors.append(f"node[{i}] missing required 'id'")
        else:
            node_ids.add(nid)
    for i, d in enumerate(graph.get("edges", [])):
        for end in ("from", "to"):
            v = d.get(end) if isinstance(d, dict) else None
            if v is None:
                errors.append(f"edge[{i}] missing required '{end}'")
            elif v not in node_ids:
                errors.append(f"edge[{i}] '{end}' references unknown node {v!r}")
    groups = graph.get("groups", [])
    group_ids = set()
    for i, d in enumerate(groups):
        gid = d.get("id") if isinstance(d, dict) else None
        if gid is None:
            errors.append(f"group[{i}] missing required 'id'")
        else:
            group_ids.add(gid)
    parent = {}
    for d in groups:
        if not isinstance(d, dict):
            continue
        gid, p = d.get("id"), d.get("parent")
        if gid is None or p is None:
            continue
        if p not in group_ids:
            errors.append(f"group {gid!r} parent references unknown group {p!r}")
        else:
            parent[gid] = p
    # group parent-chain cycle detection (the silent-hang guard)
    done = set()
    for start in list(parent):
        if start in done:
            continue
        path = []
        cur = start
        while cur in parent and cur not in done:
            if cur in path:
                cyc = path[path.index(cur):] + [cur]
                errors.append("group parent cycle: " + " -> ".join(map(repr, cyc)))
                break
            path.append(cur)
            cur = parent.get(cur)
        done.update(path)
    # journey endpoints must resolve to known nodes
    for ji, j in enumerate(graph.get("journeys", [])):
        if not isinstance(j, dict):
            continue
        for hi, hop in enumerate(j.get("hops", [])):
            if not isinstance(hop, (list, tuple)) or len(hop) < 2:
                errors.append(f"journey[{ji}] hop[{hi}] malformed: {hop!r}")
                continue
            for end in hop[:2]:
                if end not in node_ids:
                    errors.append(
                        f"journey[{ji}] hop[{hi}] references unknown node {end!r}")
    return errors


# ----------------------------------------------------------------------------
# layout
# ----------------------------------------------------------------------------

class Layout:
    def __init__(self, graph):
        errors = validate_graph(graph)
        if errors:
            raise ValueError(
                "glowmotion: cannot render — invalid graph:\n  - "
                + "\n  - ".join(errors))
        self.mode = graph.get("mode", "flow")
        self.title = graph.get("title", "diagram")
        self.nodes = [Node(n) for n in graph["nodes"]]
        self.by_id = {n.id: n for n in self.nodes}
        self.edges = [Edge(e) for e in graph.get("edges", [])]
        self.groups = [Group(g) for g in graph.get("groups", [])]
        self.group_by_id = {g.id: g for g in self.groups}
        self.journeys = graph.get("journeys", [])
        self.legend_extra = graph.get("legendExtra", [])
        # human-facing copy (optional; the model authors these so the rendered
        # file ships finished — render() falls back to neutral stubs if absent)
        self.subtitle = graph.get("subtitle")
        self.summary = graph.get("summary")   # [{accent, title, items:[...]}]
        self.footer = graph.get("footer")
        # glowmotion additions — theme + premium-finish knobs
        self.theme = graph.get("theme")               # legacy single-theme key
        self.dark_theme = graph.get("darkTheme")      # switchable pair (dark slot)
        self.light_theme = graph.get("lightTheme")    # switchable pair (light slot)
        self.theme_toggle = graph.get("themeToggle", True)  # ship both + toggle
        self.default_mode = graph.get("defaultMode", "auto")  # auto|dark|light
        self.title_highlight = graph.get("titleHighlight")  # capsule phrase
        self.signature = graph.get("signature")       # optional @byline
        self.icons = graph.get("icons", True)         # arch type glyphs
        self.effects = graph.get("effects", True)     # glow/halo/grain layer
        self.input_index = {n.id: i for i, n in enumerate(self.nodes)}
        self.notes = []
        self.lanes_r = 0
        self.lanes_l = 0
        self.lane_base_r = 0.0
        self.lane_base_l = 0.0
        # one trunk lane per (source, side): a node fanning out to several
        # off-column targets shares a single margin trunk with horizontal taps,
        # instead of N lanes marching outward into empty space.
        self._src_lane_l = {}
        self._src_lane_r = {}

    # -- sizing --
    def size_nodes(self):
        maxw = FLOW_MAXW if self.mode == "flow" else ARCH_MAXW
        for n in self.nodes:
            n.lines = wrap(n.label, maxw)
            lw = max(text_w(l) for l in n.lines)
            if self.mode == "flow":
                if n.shape == "pill":
                    n.w = min(max(text_w(n.label) + 40, 110), 150)
                    n.h = PILL_H
                else:
                    n.w = max(lw + 32, 110)
                    n.h = STEP_H if len(n.lines) == 1 else STEP_H + 14
            else:
                base = max(lw + 36, 130)
                if n.sublabel:
                    base = max(base, text_w(n.sublabel) + 36)
                n.w = base
                if n.type == "bus":
                    n.h = BUS_H
                else:
                    n.h = COMP_H if len(n.lines) == 1 else COMP_H + 16

    # -- layers --
    def assign_layers(self):
        ids = [n.id for n in self.nodes]
        if all(n.tier is not None for n in self.nodes):
            for n in self.nodes:
                n.layer = int(n.tier)
            self.back = set()
        else:
            back = find_back_edges(ids, self.edges)
            fwd = [e for i, e in enumerate(self.edges) if i not in back]
            level = longest_path_layers(ids, fwd)
            for n in self.nodes:
                n.layer = level[n.id]
            self.back = back
        # mark loop edges (flow back/self) and attach annotations
        for i, e in enumerate(self.edges):
            if self.mode == "flow" and (i in self.back):
                e.is_loop = True
                self.by_id[e.src].loop_notes.append(e.label or "")

    def _group_chain(self, n):
        chain = []
        g = self.group_by_id.get(n.group) if n.group else None
        while g is not None:
            chain.append(self.input_index.get(g.id, 0))
            chain.append(g.id)
            g = self.group_by_id.get(g.parent) if g.parent else None
        chain.reverse()
        return tuple(chain)

    def _group_set(self, n):
        s = set()
        g = self.group_by_id.get(n.group) if n.group else None
        while g is not None:
            s.add(g.id)
            g = self.group_by_id.get(g.parent) if g.parent else None
        return s

    # -- placement --
    def place(self):
        layers = {}
        for n in self.nodes:
            layers.setdefault(n.layer, []).append(n)
        vgap = FLOW_VGAP if self.mode == "flow" else ARCH_VGAP
        hgap = FLOW_HGAP if self.mode == "flow" else ARCH_HGAP
        order = sorted(layers)
        active = {}
        for L in order:
            s = set()
            for n in layers[L]:
                s |= self._group_set(n)
            active[L] = s

        y = 0.0
        for idx, L in enumerate(order):
            row = layers[L]
            row.sort(key=lambda n: (self._group_chain(n), self.input_index[n.id]))
            h = max(n.h for n in row)
            total = sum(n.w for n in row) + hgap * (len(row) - 1)
            x = CENTER - total / 2.0
            for n in row:
                n.x = x
                n.y = y + (h - n.h) / 2.0
                x += n.w + hgap
            # gap to next layer: widen where boundaries open/close so nested
            # boundary padding never makes two boundary rects overlap (C1)
            gap = vgap
            if idx + 1 < len(order):
                nxt = active[order[idx + 1]]
                closing = active[L] - nxt
                opening = nxt - active[L]
                gap = max(vgap, BOUND_PAD * (len(closing) + len(opening)) + 8)
            y += h + gap

    # -- group boxes (bottom-up) --
    def build_groups(self):
        def depth(g):
            d = 0
            while g.parent and g.parent in self.group_by_id:
                g = self.group_by_id[g.parent]
                d += 1
            return d
        for g in sorted(self.groups, key=depth, reverse=True):
            members = [n for n in self.nodes if n.group == g.id]
            child_boxes = [c.box for c in self.groups
                           if c.parent == g.id and c.box]
            xs, ys, xs2, ys2 = [], [], [], []
            for n in members:
                xs.append(n.x); ys.append(n.y); xs2.append(n.x2); ys2.append(n.y2)
            for (bx, by, bw, bh) in child_boxes:
                xs.append(bx); ys.append(by); xs2.append(bx + bw); ys2.append(by + bh)
            if not xs:
                continue
            x = min(xs) - BOUND_PAD
            yy = min(ys) - BOUND_PAD
            w = max(xs2) + BOUND_PAD - x
            hh = max(ys2) + BOUND_PAD - yy
            g.box = (x, yy, w, hh)

    # -- routing --
    def _content_bounds(self):
        xs, xs2 = [], []
        for n in self.nodes:
            xs.append(n.x); xs2.append(n.x2)
        for g in self.groups:
            if g.box:
                xs.append(g.box[0]); xs2.append(g.box[0] + g.box[2])
        return min(xs), max(xs2)

    def route(self):
        lo, hi = self._content_bounds()
        self.lane_base_r = hi + LANE_GAP
        self.lane_base_l = lo - LANE_GAP
        for e in self.edges:
            if e.is_loop:
                continue
            self._route_edge(e)

    def _layer_gap_y(self, upper_layer_bottom, target_top):
        return (upper_layer_bottom + target_top) / 2.0

    def _column_clear(self, x, y0, y1, exclude):
        """No node box straddles the vertical x within (y0, y1)."""
        lo, hi = (y0, y1) if y0 <= y1 else (y1, y0)
        for n in self.nodes:
            if n.id in exclude:
                continue
            if n.x - 3 < x < n.x2 + 3 and not (n.y2 <= lo or n.y >= hi):
                return False
        return True

    def _route_edge(self, e):
        u = self.by_id[e.src]
        v = self.by_id[e.dst]
        ux, uy = u.cx, u.y2
        vx, vtop = v.cx, v.y - EDGE_SHORT
        # exit from source bottom; if target is above (upward) start from top
        upward = v.layer < u.layer
        same = v.layer == u.layer
        if upward:
            ux, uy = u.cx, u.y
            vx, vtop = v.cx, v.y2 + EDGE_SHORT
        if (not upward) and (not same) and v.layer - u.layer == 1:
            if abs(ux - vx) < 0.6:
                e.pts = [(ux, uy), (vx, vtop)]
            else:
                midy = self._layer_gap_y(u.y2, v.y)
                e.pts = [(ux, uy), (ux, midy), (vx, midy), (vx, vtop)]
            self._set_label_pos(e, u, v)
            return
        # multi-layer downward: prefer a straight column drop (source's own
        # column, then jog above the target) when that column is clear of boxes
        # — avoids the boxy far-lane detour. Fall back to a lane only if blocked.
        if (not upward) and (not same):
            rail_b = v.y - RAIL_IN
            if self._column_clear(ux, u.y2, rail_b, {u.id, v.id}):
                e.pts = [(ux, uy), (ux, rail_b), (vx, rail_b), (vx, vtop)]
                self._set_label_pos(e, u, v)
                return
            rail_a = u.y2 + RAIL_IN
            if self._column_clear(vx, rail_a, vtop, {u.id, v.id}):
                e.pts = [(ux, uy), (ux, rail_a), (vx, rail_a), (vx, vtop)]
                self._set_label_pos(e, u, v)
                return
        if same:
            # dip just below the row and come back up into the target's bottom
            ya = max(u.y2, v.y2) + RAIL_IN
            e.pts = [(u.cx, u.y2), (u.cx, ya), (v.cx, ya),
                     (v.cx, v.y2 + EDGE_SHORT)]
            self._set_label_pos(e, u, v)
            return
        # sideways / upward / blocked -> vertical lane outside all boxes.
        # Reuse one trunk per source on each side so a fan-out (IG -> 5 modules)
        # collapses to a single bus with horizontal taps, not 5 marching lanes.
        right = u.cx >= CENTER
        if right:
            if e.src in self._src_lane_r:
                lane = self._src_lane_r[e.src]
            else:
                self.lanes_r += 1
                lane = self.lane_base_r + (self.lanes_r - 1) * LANE_STEP
                self._src_lane_r[e.src] = lane
        else:
            if e.src in self._src_lane_l:
                lane = self._src_lane_l[e.src]
            else:
                self.lanes_l += 1
                lane = self.lane_base_l - (self.lanes_l - 1) * LANE_STEP
                self._src_lane_l[e.src] = lane
        rail_a = uy + (RAIL_IN if not upward else -RAIL_IN)
        rail_b = vtop + (-RAIL_IN if not upward else RAIL_IN)
        e.pts = [(ux, uy), (ux, rail_a), (lane, rail_a),
                 (lane, rail_b), (vx, rail_b), (vx, vtop)]
        self._set_label_pos(e, u, v)

    def _set_label_pos(self, e, u, v):
        if not e.label or len(e.pts) < 2:
            return
        # midpoint of the edge's own polyline (by arc length), nudged aside so
        # fan-out branch labels never collide at the shared source point
        total = _poly_len(e.pts)
        half = total / 2.0
        acc = 0.0
        for (ax, ay), (bx, by) in zip(e.pts, e.pts[1:]):
            seg = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
            if acc + seg >= half and seg > 0:
                t = (half - acc) / seg
                e.label_pos = (ax + (bx - ax) * t + 8, ay + (by - ay) * t - 3)
                return
            acc += seg
        e.label_pos = (e.pts[0][0] + 8, e.pts[0][1])

    # -- translate to positive & viewbox --
    def normalize(self):
        xs, ys = [], []

        def acc(x, y):
            xs.append(x); ys.append(y)

        for n in self.nodes:
            acc(n.x, n.y); acc(n.x2, n.y2)
            if n.loop_notes:  # ↻ glyph + label sits to the node's right
                wid = max((text_w(s) for s in n.loop_notes), default=0.0)
                acc(n.x2 + 8 + 14 + wid + 8, n.cy)
                acc(n.x2, n.cy + 15 * len(n.loop_notes))
        for g in self.groups:
            if g.box:
                acc(g.box[0], g.box[1])
                acc(g.box[0] + g.box[2], g.box[1] + g.box[3])
        for e in self.edges:
            for (x, y) in e.pts:
                acc(x, y)
        minx, miny = min(xs), min(ys)
        dx, dy = -minx + MARGIN, -miny + MARGIN
        for n in self.nodes:
            n.x += dx; n.y += dy
        for g in self.groups:
            if g.box:
                g.box = (g.box[0] + dx, g.box[1] + dy, g.box[2], g.box[3])
        for e in self.edges:
            e.pts = [(x + dx, y + dy) for (x, y) in e.pts]
            if e.label_pos:
                e.label_pos = (e.label_pos[0] + dx, e.label_pos[1] + dy)
        # legend / cards live below; computed in render. provisional bounds:
        self.maxx = max(x + dx for x in xs)
        self.maxy = max(y + dy for y in ys)

    def run(self):
        self.size_nodes()
        self.assign_layers()
        self.place()
        self.build_groups()
        self.route()
        self.normalize()


# ----------------------------------------------------------------------------
# path serialization
# ----------------------------------------------------------------------------

def fmt(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def to_d(pts):
    if not pts:
        return ""
    out = [f"M{fmt(pts[0][0])} {fmt(pts[0][1])}"]
    px, py = pts[0]
    for (x, y) in pts[1:]:
        if abs(x - px) < 0.05:
            out.append(f"V{fmt(y)}")
        elif abs(y - py) < 0.05:
            out.append(f"H{fmt(x)}")
        else:
            out.append(f"L{fmt(x)} {fmt(y)}")
        px, py = x, y
    return " ".join(out)


# ----------------------------------------------------------------------------
# geometry dict (the contract the model consumes)
# ----------------------------------------------------------------------------

def geometry(lo):
    nodes = {}
    for n in lo.nodes:
        nodes[n.id] = {
            "x": round(n.x, 1), "y": round(n.y, 1),
            "w": round(n.w, 1), "h": round(n.h, 1),
            "shape": n.shape, "type": n.type,
            "labelLines": n.lines, "sublabel": n.sublabel,
            "loopNotes": n.loop_notes,
        }
    edges = []
    edge_d = {}
    for e in lo.edges:
        if e.is_loop:
            edges.append({"from": e.src, "to": e.dst, "kind": e.kind,
                          "label": e.label, "loop": True})
            continue
        d = to_d(e.pts)
        edge_d[(e.src, e.dst)] = d
        edges.append({"from": e.src, "to": e.dst, "kind": e.kind,
                      "d": d, "marker": e.kind != "static",
                      "label": e.label,
                      "labelPos": [round(e.label_pos[0], 1),
                                   round(e.label_pos[1], 1)] if e.label_pos else None})
    groups = {}
    for g in lo.groups:
        if g.box:
            groups[g.id] = {"label": g.label, "kind": g.kind,
                            "parent": g.parent,
                            "box": [round(v, 1) for v in g.box]}
    journeys = []
    for j in lo.journeys:
        hops = []
        for (a, b) in j.get("hops", []):
            d = edge_d.get((a, b))
            if d:
                hops.append({"from": a, "to": b, "d": d})
        if hops:
            journeys.append({"color": j.get("color"), "hops": hops})
    return {
        "mode": lo.mode,
        "title": lo.title,
        "nodes": nodes,
        "edges": edges,
        "groups": groups,
        "journeys": journeys,
        "notes": lo.notes,
        "width": round(lo.maxx + MARGIN, 1),
        "height": round(lo.maxy + BOTTOM_PAD, 1),
    }


# ----------------------------------------------------------------------------
# debug SVG renderer (geometry -> full HTML for check_diagram)
# ----------------------------------------------------------------------------

FONT_STACK = ("'JetBrains Mono', ui-monospace, 'SF Mono', 'Cascadia Code', "
              "Menlo, Consolas, monospace")


def build_palette_css(dark_T, light_T, mode, toggle):
    """The :root custom-property blocks that drive every color. When `toggle`,
    both palettes ship and switch on `[data-theme]` / prefers-color-scheme; the
    SVG and CSS below reference only var(--*), so one attribute flip repaints
    the whole file. When not `toggle`, only the dark_T block is emitted."""
    dark = theme_var_block(dark_T, mode)
    if not toggle:
        return f":root {{ {dark} }}\n"
    light = theme_var_block(light_T, mode)
    return (
        f":root {{ {dark} }}\n"
        f":root[data-theme=\"light\"] {{ {light} }}\n"
        f"@media (prefers-color-scheme: light) {{ "
        f":root:not([data-theme]) {{ {light} }} }}\n")


def build_css(maxw):
    return f"""
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: {FONT_STACK}; background: {cv('bg')};
         min-height: 100vh; padding: 2rem; color: {cv('text')}; }}
  .container {{ max-width: {maxw}px; margin: 0 auto; }}
  .header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 0.4rem; }}
  .pulse-dot {{ width: 10px; height: 10px; border-radius: 50%; background: {cv('pulse')}; }}
  h1 {{ font-size: 1.25rem; font-weight: 600; letter-spacing: -0.02em; }}
  .capsule {{ display: inline-block; background: {cv('capsule_fill')}; color: {cv('capsule_text')};
    border: 1px solid {cv('capsule_text')}; border-radius: 999px; padding: 0 14px;
    margin-left: 10px; font-size: 1.05rem; line-height: 1.75; }}
  .sig {{ margin-left: auto; color: {cv('text')}; font-size: 0.85rem; font-weight: 600;
    text-shadow: -1px 1px 0 {cv('accent_1')}, 1px -1px 0 {cv('accent_0')}; opacity: 0.85; }}
  .subtitle {{ color: {cv('subtext')}; font-size: 0.8rem; margin-bottom: 1.5rem; }}
  .diagram-card {{ border: 1px solid {cv('border')}; border-radius: 12px; position: relative;
    background: repeating-linear-gradient(0deg, {cv('grid')} 0 0.5px, transparent 0.5px 40px),
      repeating-linear-gradient(90deg, {cv('grid')} 0 0.5px, transparent 0.5px 40px), {cv('card_bg')};
    padding: 1.25rem 1rem; }}
  .ctrls {{ position: absolute; top: 12px; right: 12px; z-index: 2; display: flex; gap: 6px; }}
  .ctrl {{ background: transparent; border: 1px solid {cv('border')}; color: {cv('subtext')};
    border-radius: 6px; padding: 4px 10px; font: inherit; font-size: 11px; cursor: pointer; }}
  .ctrl:hover {{ color: {cv('text')}; border-color: {cv('border_hi')}; }}
  .footer {{ color: {cv('footer')}; font-size: 0.7rem; margin-top: 1rem; }}
  .flow {{ stroke-dasharray: 5 5; }}
  .flow-async {{ stroke-dasharray: 2 4; }}
  .flow-auth {{ stroke-dasharray: 4 4; }}
  .halo {{ opacity: 0; }}
  @media (prefers-reduced-motion: no-preference) {{
    .flow {{ animation: dashmove 0.75s linear infinite; }}
    .flow-async {{ animation: dashasync 0.9s linear infinite; }}
    .flow-auth {{ animation: dashauth 1.2s linear infinite; }}
    .pulse-dot {{ animation: pulse 2s ease-in-out infinite; }}
    .halo {{ animation: halo 4.8s ease-in-out infinite; }}
  }}
  @keyframes dashmove {{ to {{ stroke-dashoffset: -10; }} }}
  @keyframes dashasync {{ to {{ stroke-dashoffset: -12; }} }}
  @keyframes dashauth {{ to {{ stroke-dashoffset: -8; }} }}
  @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} }}
  @keyframes halo {{ 0%, 20%, 100% {{ opacity: 0; }} 7% {{ opacity: 0.8; }} 13% {{ opacity: 0.3; }} }}
  body.paused .flow, body.paused .flow-async, body.paused .flow-auth,
  body.paused .pulse-dot, body.paused .halo {{ animation-play-state: paused; }}
"""


def build_css_cards():
    return f"""
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 1rem; margin-top: 1.25rem; }}
  .card {{ border: 1px solid {cv('border')}; border-radius: 10px; background: {cv('card_bg')}; padding: 1rem 1.1rem; }}
  .card-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 0.6rem; }}
  .card-dot {{ width: 8px; height: 8px; border-radius: 50%; }}
  .card-dot.cyan {{ background: {cv('accent_0')}; }} .card-dot.violet {{ background: {cv('accent_1')}; }}
  .card-dot.rose {{ background: {cv('accent_2')}; }}
  .card h3 {{ font-size: 0.8rem; font-weight: 600; }}
  .card ul {{ list-style: none; }} .card li {{ font-size: 0.72rem; color: {cv('legend_text')}; line-height: 1.7; }}
"""


SCRIPT = """
<script>
(function () {
  // Theme toggle — flips [data-theme] on <html>; all colors are CSS vars, so
  // one attribute change repaints CSS and inline SVG together. Independent of
  // reduced-motion, so it is wired first and always.
  var root = document.documentElement;
  var tbtn = document.getElementById('themeBtn');
  if (tbtn) {
    var mq = matchMedia('(prefers-color-scheme: light)');
    var cur = function () {
      return root.getAttribute('data-theme') || (mq.matches ? 'light' : 'dark');
    };
    var sync = function () {
      var c = cur();
      tbtn.textContent = c === 'light' ? '\\u263e dark' : '\\u2600 light';
      tbtn.setAttribute('aria-label', 'Switch to ' + (c === 'light' ? 'dark' : 'light') + ' theme');
    };
    tbtn.addEventListener('click', function () {
      root.setAttribute('data-theme', cur() === 'light' ? 'dark' : 'light');
      sync();
    });
    mq.addEventListener && mq.addEventListener('change', sync);
    sync();
  }
  var svg = document.getElementById('flowsvg');
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.querySelectorAll('.dot, .trail').forEach(function (d) { d.remove(); });
    var b = document.getElementById('pauseBtn'); if (b) b.remove(); return;
  }
  var btn = document.getElementById('pauseBtn'); if (!btn) return; var paused = false;
  btn.addEventListener('click', function () {
    paused = !paused; document.body.classList.toggle('paused', paused);
    paused ? svg.pauseAnimations() : svg.unpauseAnimations();
    btn.textContent = paused ? '\\u25b6 play' : '\\u23f8 pause';
    btn.setAttribute('aria-pressed', String(paused));
  });
})();
</script>
"""

MARKER = ('<marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" '
          'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
          '<path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" '
          'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></marker>')

# Icon glyphs for arch node types. Emitted as <symbol> in <defs> and placed
# with <use> — deliberately NOT inline <path> elements, so check_diagram never
# mistakes an icon stroke for a connector (C2/C7) and check_fidelity never
# counts one toward the edge total (F4).
ICONS = {
    "frontend": '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M9 20h6M12 16v4"/>',
    "backend": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M13 15h4"/>',
    "database": ('<ellipse cx="12" cy="5.5" rx="7" ry="2.5"/>'
                 '<path d="M5 5.5v13c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-13"/>'
                 '<path d="M5 12c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5"/>'),
    "cloud": '<path d="M7 18h10a4 4 0 0 0 .8-7.9A5.5 5.5 0 0 0 7.2 9.8 3.9 3.9 0 0 0 7 18z"/>',
    "security": ('<path d="M12 3l7 3v5c0 4.4-3 7.4-7 9-4-1.6-7-4.6-7-9V6z"/>'
                 '<path d="M9 11.5l2 2 4-4"/>'),
    "bus": '<path d="M4 8h13m0 0-3-3m3 3-3 3"/><path d="M20 16H7m0 0 3-3m-3 3 3 3"/>',
    "external": ('<circle cx="12" cy="12" r="8"/>'
                 '<path d="M4 12h16M12 4c2.6 2.7 2.6 13.3 0 16-2.6-2.7-2.6-13.3 0-16z"/>'),
}

GLOW_FILTER = ('<filter id="glow" x="-120%" y="-120%" width="340%" height="340%">'
               '<feGaussianBlur stdDeviation="2.6" result="b"/>'
               '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/>'
               '</feMerge></filter>')

GRAIN_FILTER = ('<filter id="grain" x="0" y="0" width="100%" height="100%">'
                '<feTurbulence type="fractalNoise" baseFrequency="0.8" '
                'numOctaves="2" stitchTiles="stitch"/>'
                '<feColorMatrix type="matrix" values="0 0 0 0 1  0 0 0 0 1  '
                '0 0 0 0 1  0 0 0 0.05 0"/></filter>')

VIGNETTE_GRAD = ('<radialGradient id="vig" cx="50%" cy="42%" r="78%">'
                 '<stop offset="55%" stop-color="#000" stop-opacity="0"/>'
                 '<stop offset="100%" stop-color="#000" stop-opacity="0.38"/>'
                 '</radialGradient>')

SPARKLE = ('<symbol id="sparkle" viewBox="0 0 12 12">'
           '<path d="M6 1v10M1 6h10" fill="none" stroke="currentColor" '
           'stroke-width="1.4" stroke-linecap="round"/></symbol>')


def build_defs(icons_on, grain, vignette, effects):
    defs = [MARKER]
    if effects:
        defs.append(GLOW_FILTER)
        defs.append(SPARKLE)
    if grain:
        defs.append(GRAIN_FILTER)
    if vignette:
        defs.append(VIGNETTE_GRAD)
    if icons_on:
        for name, body in ICONS.items():
            defs.append(f'<symbol id="ic-{name}" viewBox="0 0 24 24" fill="none" '
                        f'stroke="currentColor" stroke-width="1.6" '
                        f'stroke-linecap="round" stroke-linejoin="round">{body}</symbol>')
    return "".join(defs)


def _node_text_svg(n):
    parts = []
    cx = n.cx
    tf = f'style="fill:{cv("text")}"'
    sf = f'style="fill:{cv("subtext")}"'
    if n.sublabel:  # arch component: label + sublabel
        ly = n.y + (n.h - 18) / 2 + 4
        if len(n.lines) == 1:
            parts.append(f'<text x="{fmt(cx)}" y="{fmt(ly)}" {tf} '
                         f'font-size="13" font-weight="500">{esc(n.lines[0])}</text>')
        else:
            parts.append(f'<text x="{fmt(cx)}" y="{fmt(ly-7)}" {tf} '
                         f'font-size="13" font-weight="500">'
                         f'<tspan x="{fmt(cx)}">{esc(n.lines[0])}</tspan>'
                         f'<tspan x="{fmt(cx)}" dy="15">{esc(n.lines[1])}</tspan></text>')
        parts.append(f'<text x="{fmt(cx)}" y="{fmt(n.y2-10)}" {sf} '
                     f'font-size="10">{esc(n.sublabel)}</text>')
    else:
        weight = "600" if n.shape == "pill" else "500"
        if len(n.lines) == 1:
            ty = n.cy + 4
            parts.append(f'<text x="{fmt(cx)}" y="{fmt(ty)}" {tf} '
                         f'font-size="13" font-weight="{weight}">{esc(n.lines[0])}</text>')
        else:
            ty = n.cy - 3
            parts.append(f'<text x="{fmt(cx)}" y="{fmt(ty)}" {tf} '
                         f'font-size="13" font-weight="{weight}">'
                         f'<tspan x="{fmt(cx)}">{esc(n.lines[0])}</tspan>'
                         f'<tspan x="{fmt(cx)}" dy="15">{esc(n.lines[1])}</tspan></text>')
    return "".join(parts)


def resolve_theme(name, warnings):
    if not name:
        return DEFAULT_THEME, THEMES[DEFAULT_THEME]
    key = str(name).strip().lower()
    if key not in THEMES:
        warnings.append(f"theme: unknown {name!r}; using {DEFAULT_THEME} "
                        f"(available: {', '.join(sorted(THEMES))})")
        key = DEFAULT_THEME
    return key, THEMES[key]


DEFAULT_DARK = "midnight"
DEFAULT_LIGHT = "daylight"

# Scalar (single-color) theme keys, emitted verbatim as CSS custom properties.
# type_style and accents expand into their own vars separately.
_SCALAR_KEYS = [
    "bg", "grid", "card_bg", "border", "border_hi", "text", "subtext",
    "legend_text", "footer", "flow_node_fill", "flow_node_stroke",
    "flow_pill_fill", "flow_pill_stroke", "flow_conn", "flow_dot",
    "arch_conn", "arch_async", "arch_auth", "arch_dot", "node_base",
    "region", "subnet", "capsule_fill", "capsule_text",
]


def cv(key):
    """Reference a themed color as a CSS variable: 'flow_conn' -> var(--flow-conn)."""
    return f"var(--{key.replace('_', '-')})"


def type_fill_v(name):
    return f"var(--t-{name}-fill)"


def type_stroke_v(name):
    return f"var(--t-{name}-stroke)"


def accent_v(i):
    return f"var(--accent-{i})"


def theme_var_block(T, mode):
    """Emit one theme's tokens as `--name: value;` declarations (no selector)."""
    out = []
    for k in _SCALAR_KEYS:
        out.append(f"--{k.replace('_', '-')}:{T[k]};")
    for name, (fill, stroke, _leg) in T["type_style"].items():
        out.append(f"--t-{name}-fill:{fill};--t-{name}-stroke:{stroke};")
    for i, a in enumerate(T["accents"]):
        out.append(f"--accent-{i}:{a};")
    out.append(f"--pulse:{T['flow_dot'] if mode == 'flow' else T['arch_dot']};")
    return "".join(out)


def resolve_palette(lo, warnings):
    """Resolve the (dark, light) theme pair + toggle behavior for a switchable
    file. `theme` (legacy single-theme key) is honored: a light theme routes to
    the light slot, a dark one to the dark slot; the OTHER slot takes its
    default so the file is still switchable unless `themeToggle: false`."""
    def pick(name, warn_label):
        if not name:
            return None
        k = str(name).strip().lower()
        if k not in THEMES:
            warnings.append(f"{warn_label}: unknown {name!r}; ignoring "
                            f"(available: {', '.join(sorted(THEMES))})")
            return None
        return k

    dark = pick(lo.dark_theme, "darkTheme")
    light = pick(lo.light_theme, "lightTheme")
    legacy = pick(lo.theme, "theme")
    if legacy:
        if THEMES[legacy].get("is_light"):
            light = light or legacy
        else:
            dark = dark or legacy
    # guard against a light theme landing in the dark slot (or vice versa)
    if dark and THEMES[dark].get("is_light"):
        light = light or dark
        dark = None
    if light and not THEMES[light].get("is_light"):
        dark = dark or light
        light = None
    dark = dark or DEFAULT_DARK
    light = light or DEFAULT_LIGHT

    toggle = bool(lo.theme_toggle)
    mode = str(lo.default_mode).strip().lower()
    if mode not in ("auto", "dark", "light"):
        warnings.append(f"defaultMode: unknown {lo.default_mode!r}; using auto")
        mode = "auto"
    return dark, light, toggle, mode


def render(lo, geom):
    mode = lo.mode
    warnings = []
    dark_name, light_name, toggle, default_mode = resolve_palette(lo, warnings)
    dark_T, light_T = THEMES[dark_name], THEMES[light_name]
    effects = bool(lo.effects)
    # grain/vignette are dark-canvas garnish that can't co-switch cleanly onto a
    # light palette — they are suppressed whenever the file is switchable (the
    # new default). glow / trails / halos / sparkles read on both and stay.
    grain = effects and (not toggle) and dark_T["grain"]
    vignette = effects and (not toggle) and dark_T["vignette"]
    icons_on = bool(lo.icons) and mode != "flow"
    W = geom["width"]
    H = geom["height"]

    # boundaries (arch) first — static containers
    bound_svg = []
    used_types = []          # type names, first-seen order (legend order)
    if mode != "flow":
        for g in lo.groups:
            if not g.box:
                continue
            x, y, w, h = g.box
            if g.kind == "subnet":
                stroke, dash, fs = cv("subnet"), "4 4", 10
                rx = 8
            else:
                stroke, dash, fs = cv("region"), "8 4", 11
                rx = 12
            bound_svg.append(
                f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                f'rx="{rx}" fill="none" style="stroke:{stroke}" stroke-width="1" '
                f'stroke-dasharray="{dash}" opacity="0.6" data-grp-id="{esc(g.id)}"/>')
            bound_svg.append(
                f'<text x="{fmt(x+14)}" y="{fmt(y+18)}" style="fill:{stroke}" '
                f'font-size="{fs}" opacity="0.9">{esc(g.label)}</text>')

    # connectors
    conn = ['<g fill="none">']
    label_svg = []
    for e in lo.edges:
        if e.is_loop:
            continue
        d = to_d(e.pts)
        if mode == "flow":
            stroke = cv("flow_conn")
            width = "1.5" if e.kind == "main" else "1"
            opacity = "0.85"
        else:
            stroke = (cv("arch_async") if e.kind == "async"
                      else cv("arch_auth") if e.kind == "auth" else cv("arch_conn"))
            width = "1.5" if e.kind == "main" else "1"
            opacity = "1"
        cls = ("flow-async" if e.kind == "async"
               else "flow-auth" if e.kind == "auth"
               else "" if e.kind == "static" else "flow")
        marker = "" if e.kind == "static" else ' marker-end="url(#arrow)"'
        clsattr = f' class="{cls}"' if cls else ""
        conn.append(f'<path{clsattr} d="{d}" style="stroke:{stroke}" '
                    f'stroke-width="{width}" opacity="{opacity}"{marker}/>')
        if e.label and e.label_pos:
            lx, ly = e.label_pos
            label_svg.append(f'<text x="{fmt(lx)}" y="{fmt(ly)}" style="fill:{cv("subtext")}" '
                             f'font-size="10">{esc(e.label)}</text>')
    conn.append('</g>')

    # loop annotations
    for n in lo.nodes:
        off = 0
        for note in n.loop_notes:
            lx = n.x2 + 8
            ly = n.cy + 4 + off
            label_svg.append(f'<text x="{fmt(lx)}" y="{fmt(ly)}" style="fill:{cv("subtext")}" '
                             f'font-size="11">↻</text>')
            if note:
                label_svg.append(f'<text x="{fmt(lx+14)}" y="{fmt(ly)}" '
                                 f'style="fill:{cv("subtext")}" font-size="10">{esc(note)}</text>')
            off += 15

    # journeys / dots — main dot gets the #glow filter; two `trail` circles ride
    # the SAME path 0.09s/0.18s behind at falling size/opacity (the lanshu comet).
    # A journey without an explicit color takes the theme accent cycle (a CSS var
    # so it re-tints on theme switch); the first journey matches the "request in
    # flight" legend dot. An explicit color is a fixed literal in both modes.
    dot_svg = []
    dot_default_vars = ([cv("flow_dot")] if mode == "flow" else [cv("arch_dot")]) \
        + [accent_v(i) for i in range(len(dark_T["accents"]))]
    edge_d = {(e.src, e.dst): to_d(e.pts) for e in lo.edges if not e.is_loop}
    edge_pts = {(e.src, e.dst): e.pts for e in lo.edges if not e.is_loop}
    for ji, j in enumerate(lo.journeys):
        color = safe_color(j.get("color"), dot_default_vars[ji % len(dot_default_vars)],
                           f"journey {ji}", warnings)
        hops = [h for h in j.get("hops", []) if (h[0], h[1]) in edge_d]
        if not hops:
            continue
        prev_id = None
        last_id = f"j{ji}_{len(hops)-1}"
        for hi, (a, b) in enumerate(hops):
            d = edge_d[(a, b)]
            mid = f"j{ji}_{hi}"
            if hi == 0:
                begin = f"0s;{last_id}.end+0.6s"
            else:
                begin = f"{prev_id}.end+0.3s"
            dur = min(DOT_DUR_MAX,
                      max(DOT_DUR_MIN, _poly_len(edge_pts[(a, b)]) / DOT_SPEED))
            filt = ' filter="url(#glow)"' if effects else ""
            dot_svg.append(
                f'<circle r="3.5" class="dot" style="fill:{color}"{filt}>'
                f'<animateMotion id="{mid}" dur="{dur:.1f}s" begin="{begin}" '
                f'fill="freeze" path="{d}"/></circle>')
            if effects:
                for r, op, lag in ((2.4, 0.5, 0.09), (1.7, 0.28, 0.18)):
                    dot_svg.append(
                        f'<circle r="{r}" class="trail" style="fill:{color}" opacity="{op}">'
                        f'<animateMotion dur="{dur:.1f}s" begin="{mid}.begin+{lag}s" '
                        f'fill="freeze" path="{d}"/></circle>')
            prev_id = mid

    # halo pulse targets — nodes a journey touches, in first-touch order; each
    # halo rect shares its node rect's exact geometry (checker-dedupe keeps C1
    # clean) and pulses on a staggered delay (the lanshu module-highlight cycle).
    halo_order = []
    if effects:
        for j in lo.journeys:
            for hop in j.get("hops", []):
                for nid in hop[:2]:
                    if nid not in halo_order and nid in lo.by_id:
                        halo_order.append(nid)

    def halo_rect(n, stroke, rx):
        if not effects or n.id not in halo_order:
            return ""
        delay = halo_order.index(n.id) * 0.6
        return (f'<rect x="{fmt(n.x)}" y="{fmt(n.y)}" width="{fmt(n.w)}" '
                f'height="{fmt(n.h)}" rx="{rx}" fill="none" '
                f'stroke-width="2" class="halo" filter="url(#glow)" '
                f'style="stroke:{stroke};animation-delay:{delay:.1f}s"/>')

    # nodes
    node_svg = []
    type_style = dark_T["type_style"]   # geometry-independent; legend labels only
    for n in lo.nodes:
        if mode == "flow":
            if n.shape == "pill":
                node_svg.append(
                    f'<rect x="{fmt(n.x)}" y="{fmt(n.y)}" width="{fmt(n.w)}" '
                    f'height="{fmt(n.h)}" rx="20" '
                    f'style="fill:{cv("flow_pill_fill")};stroke:{cv("flow_pill_stroke")}" '
                    f'stroke-width="1.5"/>')
                node_svg.append(halo_rect(n, cv("flow_pill_stroke"), 20))
            elif n.shape == "decision":
                node_svg.append(
                    f'<rect x="{fmt(n.x)}" y="{fmt(n.y)}" width="{fmt(n.w)}" '
                    f'height="{fmt(n.h)}" rx="8" '
                    f'style="fill:{cv("flow_node_fill")};stroke:{cv("flow_node_stroke")}" '
                    f'stroke-dasharray="4 3"/>')
                node_svg.append(halo_rect(n, cv("flow_node_stroke"), 8))
            else:
                node_svg.append(
                    f'<rect x="{fmt(n.x)}" y="{fmt(n.y)}" width="{fmt(n.w)}" '
                    f'height="{fmt(n.h)}" rx="8" '
                    f'style="fill:{cv("flow_node_fill")};stroke:{cv("flow_node_stroke")}"/>')
                node_svg.append(halo_rect(n, cv("flow_node_stroke"), 8))
            node_svg.append(_node_text_svg(n))
        else:
            tname = n.type if n.type in type_style else "external"
            if tname not in used_types:
                used_types.append(tname)
            # semStroke (explicit classDef retention) is a fixed literal; else the
            # themed type stroke var (re-tints on switch).
            st = safe_color(n.sem_stroke, type_stroke_v(tname),
                            f"node {n.id} semStroke", warnings)
            fillv = type_fill_v(tname)
            _nd = safe_dash(n.sem_dash, f"node {n.id} semDash", warnings)
            dash = f' stroke-dasharray="{_nd}"' if _nd else ""
            # group membership (resolved ancestor chain) for the C9 structural
            # check — lets check_diagram judge "node geometrically inside a group
            # box it isn't a member of" from the HTML alone (no graph JSON needed
            # at generation-time Step 6). Empty for ungrouped nodes.
            grp = esc(" ".join(sorted(lo._group_set(n))))
            node_svg.append(
                f'<rect x="{fmt(n.x)}" y="{fmt(n.y)}" width="{fmt(n.w)}" '
                f'height="{fmt(n.h)}" rx="8" style="fill:{cv("node_base")}" data-grp="{grp}"/>')
            node_svg.append(
                f'<rect x="{fmt(n.x)}" y="{fmt(n.y)}" width="{fmt(n.w)}" '
                f'height="{fmt(n.h)}" rx="8" style="fill:{fillv};stroke:{st}" '
                f'stroke-width="1.5"{dash} data-grp="{grp}"/>')
            node_svg.append(halo_rect(n, st, 8))
            if icons_on and n.type in ICONS:
                # <use> glyph: defs symbol, invisible to both checkers by design
                node_svg.append(
                    f'<use href="#ic-{n.type}" x="{fmt(n.x+5)}" y="{fmt(n.y+6)}" '
                    f'width="12" height="12" style="color:{st}" opacity="0.65"/>')
            node_svg.append(_node_text_svg(n))

    # legend (arch): below everything
    legend_svg = []
    if mode != "flow":
        ly = H - BOTTOM_PAD + 6
        lx = MARGIN
        for tname in used_types:
            leg = type_style[tname][2]
            legend_svg.append(
                f'<rect x="{fmt(lx)}" y="{fmt(ly)}" width="12" height="12" rx="3" '
                f'style="fill:{type_fill_v(tname)};stroke:{type_stroke_v(tname)}"/>')
            legend_svg.append(
                f'<text x="{fmt(lx+18)}" y="{fmt(ly+10)}" style="fill:{cv("legend_text")}" '
                f'font-size="11">{esc(leg)}</text>')
            lx += 22 + text_w(leg) + 28
        legend_svg.append(
            f'<circle cx="{fmt(lx+6)}" cy="{fmt(ly+6)}" r="3.5" style="fill:{cv("arch_dot")}"/>')
        legend_svg.append(
            f'<text x="{fmt(lx+16)}" y="{fmt(ly+10)}" style="fill:{cv("legend_text")}" '
            f'font-size="11">request in flight</text>')
        lx += 16 + text_w("request in flight") + 28
        # semantic classDef legend entries (preserved stroke variants)
        if lo.legend_extra:
            ly2 = ly + 22
            lx = MARGIN
            for ex in lo.legend_extra:
                _xlbl = ex.get("label", "?")
                _xd = safe_dash(ex.get("dash"), f"legendExtra {_xlbl}", warnings)
                exd = f' stroke-dasharray="{_xd}"' if _xd else ""
                _xs = safe_color(ex.get("stroke"), cv("legend_text"),
                                 f"legendExtra {_xlbl}", warnings)
                legend_svg.append(
                    f'<rect x="{fmt(lx)}" y="{fmt(ly2)}" width="12" height="12" '
                    f'rx="3" fill="none" style="stroke:{_xs}"{exd}/>')
                legend_svg.append(
                    f'<text x="{fmt(lx+18)}" y="{fmt(ly2+10)}" style="fill:{cv("legend_text")}" '
                    f'font-size="11">{esc(ex["label"])}</text>')
                lx += 22 + text_w(ex["label"]) + 28
            H = H + 24
            W = max(W, lx + 10)
        W = max(W, lx + 10)
        H = H + 12

    svg = []
    # ARIA: wire title/desc to the SVG and name the diagram type. Without the
    # id + aria-labelledby/describedby link a screen reader sees role=img with no
    # accessible name; aria-roledescription announces what kind of diagram it is.
    roledesc = "flowchart" if mode == "flow" else "architecture diagram"
    svg.append(f'<svg id="flowsvg" width="100%" viewBox="0 0 {fmt(W)} {fmt(H)}" '
               f'role="img" aria-roledescription="{roledesc}" '
               f'aria-labelledby="flowsvg-title" aria-describedby="flowsvg-desc">')
    svg.append(f'<title id="flowsvg-title">{esc(lo.title)} animated diagram</title>')
    svg.append(f'<desc id="flowsvg-desc">Top-down {mode} diagram; dashed connectors '
               f'animate in the direction of flow and glowing dots ride the main paths.</desc>')
    svg.append(f'<defs>{build_defs(icons_on, grain, vignette, effects)}</defs>')
    svg.extend(bound_svg)
    svg.extend(conn)
    svg.extend(label_svg)
    svg.append('<g>')
    svg.extend(dot_svg)
    svg.append('</g>')
    svg.append(f'<g font-family="{FONT_STACK}" text-anchor="middle">')
    svg.extend(node_svg)
    svg.append('</g>')
    if legend_svg:
        svg.append(f'<g font-family="{FONT_STACK}" font-size="11">')
        svg.extend(legend_svg)
        svg.append('</g>')
    if effects:
        # corner sparkles — pure garnish, <use> so the checkers never see them
        nacc = len(dark_T["accents"])
        for si, (sx, sy) in enumerate([(10, 8), (W - 24, 12),
                                       (8, H - 24), (W - 28, H - 28)]):
            svg.append(f'<use href="#sparkle" x="{fmt(sx)}" y="{fmt(sy)}" '
                       f'width="12" height="12" style="color:{accent_v(si % nacc)}" '
                       f'opacity="0.35"/>')
    # premium finish: grain + vignette are full-bleed scenery rects painted last
    # (check_diagram excludes ~full-viewBox rects from its box set by design)
    if grain:
        svg.append(f'<rect x="0" y="0" width="{fmt(W)}" height="{fmt(H)}" '
                   f'fill="#000" filter="url(#grain)" opacity="0.55"/>')
    if vignette:
        svg.append(f'<rect x="0" y="0" width="{fmt(W)}" height="{fmt(H)}" '
                   f'fill="url(#vig)"/>')
    svg.append('</svg>')

    maxw = 960 if mode == "flow" else 1100
    css = build_palette_css(dark_T, light_T, mode, toggle) + build_css(maxw)
    if mode != "flow":
        css += build_css_cards()
    cards = ""
    if mode != "flow":
        if lo.summary:
            # model-authored summary cards (architecture convention: 3 cards)
            blocks = []
            for c in lo.summary:
                accent = c.get("accent", "cyan")
                if accent not in ("cyan", "violet", "rose"):
                    accent = "cyan"
                items = "".join(f"<li>• {esc(it)}</li>"
                                for it in c.get("items", []))
                blocks.append(
                    f'<div class="card"><div class="card-header">'
                    f'<div class="card-dot {accent}"></div>'
                    f'<h3>{esc(c.get("title", ""))}</h3></div>'
                    f'<ul>{items}</ul></div>')
            cards = f'<div class="cards">{"".join(blocks)}</div>'
        else:
            cards = (
                '<div class="cards">'
                '<div class="card"><div class="card-header"><div class="card-dot cyan">'
                '</div><h3>Request path</h3></div><ul><li>• glowing dot rides the '
                'main journey</li><li>• tier by tier</li></ul></div>'
                '<div class="card"><div class="card-header"><div class="card-dot violet">'
                '</div><h3>Data layer</h3></div><ul><li>• stores and caches</li>'
                '<li>• accent components</li></ul></div>'
                '<div class="card"><div class="card-header"><div class="card-dot rose">'
                '</div><h3>Boundaries</h3></div><ul><li>• regions and subnets</li>'
                '<li>• dashed containment</li></ul></div></div>')

    cap = (f'<span class="capsule">{esc(lo.title_highlight)}</span>'
           if lo.title_highlight else "")
    sig = f'<div class="sig">{esc(lo.signature)}</div>' if lo.signature else ""
    # initial theme: auto -> follow OS (no attribute); dark/light -> pinned
    html_attr = "" if (not toggle or default_mode == "auto") \
        else f' data-theme="{default_mode}"'
    theme_btn = ('<button class="ctrl" id="themeBtn" aria-label="Switch theme">'
                 '☀ light</button>') if toggle else ""
    if toggle:
        pair = f"{dark_name} / {light_name} · switchable"
    else:
        pair = f"{dark_name} theme"
    footer = lo.footer if lo.footer else f"glowmotion · {mode} mode · {pair}"
    html = f"""<!DOCTYPE html>
<html lang="en"{html_attr}>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="{'light dark' if toggle else 'dark'}">
<title>{esc(lo.title)} — glowmotion</title>
<style>{css}</style>
</head>
<body>
<div class="container">
  <div class="header"><div class="pulse-dot"></div><h1>{esc(lo.title)}{cap}</h1>{sig}</div>
  <p class="subtitle">{esc(lo.subtitle) if lo.subtitle else f"Animated {mode} diagram"}</p>
  <div class="diagram-card">
    <div class="ctrls">{theme_btn}<button class="ctrl" id="pauseBtn" aria-pressed="false">⏸ pause</button></div>
    {''.join(svg)}
  </div>
  {cards}
  <p class="footer">{esc(footer)}</p>
</div>
{SCRIPT}
</body>
</html>"""
    if warnings:
        seen = []
        for w in warnings:
            if w not in seen:
                seen.append(w)
        sys.stderr.write(
            "glowmotion: style fallback(s) applied — output rendered with "
            "engine defaults, not the supplied value(s):\n")
        for w in seen:
            sys.stderr.write(f"  - {w}\n")
    return html


def _poly_len(pts):
    total = 0.0
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        total += ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
    return total


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main():
    import argparse
    ap = argparse.ArgumentParser(
        prog="glowmotion layout.py",
        description="Deterministic layout + premium render for glowmotion "
                    "diagrams. Without --render, prints geometry JSON.")
    ap.add_argument("graph", help="semantic graph JSON (see references/graph-format.md)")
    ap.add_argument("--render", "--emit-svg", dest="render", metavar="OUT_HTML",
                    help="write the complete, self-contained HTML here")
    ns = ap.parse_args()
    with open(ns.graph, encoding="utf-8") as fh:
        graph = json.load(fh)
    try:
        lo = Layout(graph)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(2)
    lo.run()
    geom = geometry(lo)
    if ns.render:
        html = render(lo, geom)
        with open(ns.render, "w", encoding="utf-8") as fh:
            fh.write(html)
        print(f"wrote {ns.render}")
    else:
        print(json.dumps(geom, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

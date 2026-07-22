#!/usr/bin/env python3
"""Deterministic structural checker for glowmotion HTML diagrams.

Inherited from dashmotion's checker (C1-C9), plus C10: animation presence —
lanshu's gif_has_motion lesson, vectorized. Failure classes:

  C1 overlap        two rects partially intersect (containment is fine)
  C2 through-box    a connector segment crosses a node it doesn't terminate at
  C3 dash-seam      |stroke-dashoffset delta| is not a multiple of the dasharray period
  C4 out-of-bounds  any coordinate outside the viewBox (or negative)
  C5 dot-off-line   an animateMotion point strays from every connector path
  C6 black-fill     a multi-segment connector with effective fill != none
  C7 endpoint-pierce a connector endpoint sits deep inside a node box
  C8 begin-ref      a SMIL begin="X.end+..." references a missing id
  C9 group-member   a node sits fully inside a group box it is not a member of
                    (the silent class C1 can't see: containment is C1-exempt)
  C10 no-motion     the animation layer is missing: no connector resolves to an
                    animated dash class, no traveling dot at all, or the dot
                    budget is blown (>8 main dots reads as noise, not signal)

Not checked (documented limitation): text/label collisions (needs font
metrics), boundary 20px padding, legend placement.

Usage: python3 check_diagram.py file1.html [file2.html ...] [--json]
Exit code 0 always; results go to stdout.
"""

import json
import math
import re
import sys
import xml.etree.ElementTree as ET

SAMPLE_STEP = 2.0          # px between samples along a path
INSIDE_MARGIN = 2.0        # how far inside a rect counts as "inside"
TERMINAL_PAD = 8.0         # endpoint within rect+pad => that rect is a terminal
ENDPOINT_SKIP = 6.0        # arc-length near path ends excluded from C2
ON_LINE_TOL = 2.5          # max distance from a dot sample to a connector (C5)
CONTAIN_TOL = 0.6          # tolerance for rect containment tests


# ---------- geometry ----------

class Rect:
    def __init__(self, x, y, w, h, el=None):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.el = el
        self.is_container = False

    @property
    def x2(self): return self.x + self.w
    @property
    def y2(self): return self.y + self.h

    def contains_rect(self, o, tol=CONTAIN_TOL):
        return (self.x <= o.x + tol and self.y <= o.y + tol and
                self.x2 >= o.x2 - tol and self.y2 >= o.y2 - tol)

    def intersects(self, o):
        return not (self.x2 <= o.x or o.x2 <= self.x or
                    self.y2 <= o.y or o.y2 <= self.y)

    def contains_point(self, px, py, margin=0.0):
        return (self.x + margin < px < self.x2 - margin and
                self.y + margin < py < self.y2 - margin)

    def expanded(self, pad):
        return Rect(self.x - pad, self.y - pad, self.w + 2 * pad, self.h + 2 * pad)

    def label(self):
        return f"rect({self.x:g},{self.y:g} {self.w:g}x{self.h:g})"


def seg_point_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


# ---------- path parsing ----------

_TOKEN = re.compile(r"([MLHVCSQTAZmlhvcsqtaz])|(-?\d*\.?\d+(?:[eE][-+]?\d+)?)")


def parse_path(d):
    """Return (polyline_points, ok). Curves are flattened; A/S/T unsupported."""
    tokens = []
    for m in _TOKEN.finditer(d or ""):
        tokens.append(m.group(1) if m.group(1) else float(m.group(2)))
    pts, i, cmd = [], 0, None
    cx = cy = sx = sy = 0.0
    ok = True

    def need(n):
        return i + n <= len(tokens) and all(isinstance(t, float) for t in tokens[i:i + n])

    while i < len(tokens):
        t = tokens[i]
        if isinstance(t, str):
            cmd = t
            i += 1
            if cmd in ("Z", "z"):
                if pts:
                    pts.append((sx, sy))
                continue
        if cmd is None:
            return pts, False
        rel = cmd.islower()
        c = cmd.upper()
        if c == "M":
            if not need(2): return pts, False
            x, y = tokens[i], tokens[i + 1]; i += 2
            cx, cy = (cx + x, cy + y) if rel else (x, y)
            sx, sy = cx, cy
            pts.append((cx, cy))
            cmd = "l" if rel else "L"  # subsequent implicit pairs are lineto
        elif c == "L":
            if not need(2): return pts, False
            x, y = tokens[i], tokens[i + 1]; i += 2
            cx, cy = (cx + x, cy + y) if rel else (x, y)
            pts.append((cx, cy))
        elif c == "H":
            if not need(1): return pts, False
            x = tokens[i]; i += 1
            cx = cx + x if rel else x
            pts.append((cx, cy))
        elif c == "V":
            if not need(1): return pts, False
            y = tokens[i]; i += 1
            cy = cy + y if rel else y
            pts.append((cx, cy))
        elif c in ("C", "Q"):
            n = 6 if c == "C" else 4
            if not need(n): return pts, False
            args = tokens[i:i + n]; i += n
            if rel:
                args = [args[k] + (cx if k % 2 == 0 else cy) for k in range(n)]
            p0 = (cx, cy)
            ctrl = [(args[k], args[k + 1]) for k in range(0, n, 2)]
            for step in range(1, 17):
                u = step / 16.0
                if c == "Q":
                    bx = (1-u)**2*p0[0] + 2*(1-u)*u*ctrl[0][0] + u**2*ctrl[1][0]
                    by = (1-u)**2*p0[1] + 2*(1-u)*u*ctrl[0][1] + u**2*ctrl[1][1]
                else:
                    bx = ((1-u)**3*p0[0] + 3*(1-u)**2*u*ctrl[0][0]
                          + 3*(1-u)*u**2*ctrl[1][0] + u**3*ctrl[2][0])
                    by = ((1-u)**3*p0[1] + 3*(1-u)**2*u*ctrl[0][1]
                          + 3*(1-u)*u**2*ctrl[1][1] + u**3*ctrl[2][1])
                pts.append((bx, by))
            cx, cy = pts[-1]
        else:  # A, S, T — not used by the skill's templates
            ok = False
            break
    return pts, ok


def sample_polyline(pts, step=SAMPLE_STEP):
    """(arc_pos, x, y) samples every `step` px, endpoints included."""
    out, acc = [], 0.0
    if not pts:
        return out
    out.append((0.0, pts[0][0], pts[0][1]))
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        seg = math.hypot(bx - ax, by - ay)
        n = max(1, int(seg / step))
        for k in range(1, n + 1):
            u = k / n
            out.append((acc + seg * u, ax + (bx - ax) * u, ay + (by - ay) * u))
        acc += seg
    return out


# ---------- document parsing ----------

def extract_svg(html):
    m = re.search(r"<svg\b[\s\S]*?</svg>", html)
    if not m:
        return None
    svg = m.group(0)
    svg = re.sub(r"&(?!#?\w+;)", "&amp;", svg)       # bare ampersands
    svg = re.sub(r"\sxlink:href=", " href=", svg)
    return svg


def parse_css(html):
    """class -> {dasharray, anim}, keyframes -> dashoffset delta."""
    classes, keyframes = {}, {}
    for style in re.findall(r"<style[^>]*>([\s\S]*?)</style>", html):
        for name, body in re.findall(
                r"@keyframes\s+([\w-]+)\s*\{((?:[^{}]*\{[^{}]*\})*[^{}]*)\}", style):
            off = re.search(r"stroke-dashoffset:\s*(-?[\d.]+)", body)
            if off:
                keyframes[name] = abs(float(off.group(1)))
        flat = re.sub(r"@keyframes\s+[\w-]+\s*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", style)
        flat = re.sub(r"@media[^{]*\{", "", flat)
        for sel, body in re.findall(r"\.([\w-]+)\s*\{([^{}]*)\}", flat):
            d = classes.setdefault(sel, {})
            da = re.search(r"stroke-dasharray:\s*([\d.\s,]+);", body)
            if da:
                d["dasharray"] = [float(v) for v in re.split(r"[\s,]+", da.group(1).strip()) if v]
            an = re.search(r"animation:\s*([\w-]+)", body)
            if an:
                d["anim"] = an.group(1)
            fi = re.search(r"fill:\s*([^;]+);", body)
            if fi:
                d["fill"] = fi.group(1).strip()
    return classes, keyframes


def walk(el, ancestors, out):
    out.append((el, list(ancestors)))
    ancestors.append(el)
    for ch in el:
        walk(ch, ancestors, out)
    ancestors.pop()


def tag(el):
    return el.tag.split("}")[-1]


def effective_attr(el, ancestors, name):
    if el.get(name) is not None:
        return el.get(name)
    for a in reversed(ancestors):
        if a.get(name) is not None:
            return a.get(name)
    return None


def parse_dasharray_attr(val):
    if not val:
        return None
    try:
        return [float(v) for v in re.split(r"[\s,]+", val.strip()) if v]
    except ValueError:
        return None


# ---------- the checks ----------

def check_file(path):
    html = open(path, encoding="utf-8").read()
    violations = []
    add = lambda code, msg: violations.append({"code": code, "msg": msg})

    svg_src = extract_svg(html)
    if not svg_src:
        add("PARSE", "no <svg> element found")
        return violations
    try:
        root = ET.fromstring(svg_src)
    except ET.ParseError as e:
        add("PARSE", f"SVG is not parseable XML: {e}")
        return violations

    vb = (root.get("viewBox") or "").split()
    if len(vb) != 4:
        add("C4", "missing/odd viewBox")
        return violations
    vb_x, vb_y, vb_w, vb_h = (float(v) for v in vb)
    if vb_x != 0 or vb_y != 0:
        add("C4", f"viewBox origin not 0 0: {vb_x:g} {vb_y:g}")

    classes, keyframes = parse_css(html)
    nodes_all = []
    for el, anc in (lambda L: (walk(root, [], L), L)[1])([]):
        nodes_all.append((el, anc))

    in_defs = lambda anc: any(tag(a) in ("defs", "marker") for a in anc)

    # -- collect rects --
    rects = []
    for el, anc in nodes_all:
        if tag(el) != "rect" or in_defs(anc):
            continue
        try:
            r = Rect(float(el.get("x", 0)), float(el.get("y", 0)),
                     float(el.get("width", 0)), float(el.get("height", 0)), el)
        except (TypeError, ValueError):
            continue
        rects.append(r)

    # dedupe identical geometry (opaque base + styled pair)
    uniq = {}
    for r in rects:
        uniq.setdefault((round(r.x, 1), round(r.y, 1), round(r.w, 1), round(r.h, 1)), r)
    rects = list(uniq.values())

    # full-bleed background rects (cover ~whole viewBox) are scenery
    rects = [r for r in rects if not (r.w >= vb_w * 0.98 and r.h >= vb_h * 0.98)]

    # containers: any rect that fully contains another rect
    for a in rects:
        for b in rects:
            if a is not b and a.contains_rect(b) and (a.w > b.w + 1 or a.h > b.h + 1):
                a.is_container = True
                break
    boxes = [r for r in rects if not r.is_container]

    # -- C1: partial overlap --
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            if a.intersects(b) and not a.contains_rect(b) and not b.contains_rect(a):
                add("C1", f"partial overlap: {a.label()} vs {b.label()}")

    # -- C9: group membership --
    # A node fully inside a group box it doesn't belong to is the silent
    # corruption class group-blind layering produces (e.g. a region box swallows
    # a foreign node, or a subnet box swallows its parent's loose node). C1 can't
    # see it because full containment is C1-exempt (subnet-in-region is a valid
    # containment). The renderer embeds data-grp-id on each group box and
    # data-grp (the node's resolved ancestor-group set) on each node rect, so the
    # judgement is made from the HTML alone — no graph JSON needed at Step 6.
    grp_boxes = [r for r in rects if r.el is not None and r.el.get("data-grp-id")]
    grp_nodes = [r for r in rects if r.el is not None and r.el.get("data-grp") is not None]
    for box in grp_boxes:
        gid = box.el.get("data-grp-id")
        for nd in grp_nodes:
            members = set((nd.el.get("data-grp") or "").split())
            if gid in members:
                continue
            if box.contains_rect(nd):
                add("C9", f"node {nd.label()} is inside group box \"{gid}\" "
                          f"{box.label()} but is not a member "
                          f"(node groups: {sorted(members) or 'none'})")

    # -- collect connector paths --
    connectors = []   # (points, samples, el, anc, unsupported)
    for el, anc in nodes_all:
        if tag(el) != "path" or in_defs(anc):
            continue
        pts, ok = parse_path(el.get("d", ""))
        if len(pts) < 2:
            continue
        connectors.append((pts, sample_polyline(pts), el, anc, not ok))

    # -- C2 / C7 / C4 / C6 per connector --
    for pts, samples, el, anc, unsupported in connectors:
        if unsupported:
            continue  # can't reason about unflattened commands
        total = samples[-1][0] if samples else 0.0
        ends = [pts[0], pts[-1]]
        terminals = [b for b in boxes
                     if any(b.expanded(TERMINAL_PAD).contains_point(px, py) for px, py in ends)]
        hit = set()
        for arc, px, py in samples:
            if px < vb_x - 0.5 or px > vb_w + 0.5 or py < vb_y - 0.5 or py > vb_h + 0.5:
                add("C4", f"path point ({px:g},{py:g}) outside viewBox in d=\"{el.get('d','')[:60]}\"")
                break
        for arc, px, py in samples:
            if arc < ENDPOINT_SKIP or arc > total - ENDPOINT_SKIP:
                continue
            for b in boxes:
                if b in terminals or id(b) in hit:
                    continue
                if b.contains_point(px, py, INSIDE_MARGIN):
                    add("C2", f"connector crosses {b.label()} (d=\"{el.get('d','')[:60]}\")")
                    hit.add(id(b))
        for px, py in ends:
            for b in boxes:
                if b.contains_point(px, py, 1.5):
                    add("C7", f"endpoint ({px:g},{py:g}) pierces {b.label()}")

        if len(pts) > 2:  # multi-segment open path: black default fill is fatal
            fill = el.get("fill")
            if fill is None:
                fill = effective_attr(el, anc, "fill")
            if fill is None:
                for cls in (el.get("class") or "").split():
                    fill = classes.get(cls, {}).get("fill")
                    if fill:
                        break
            if fill is None or fill.strip().lower() not in ("none", "transparent"):
                add("C6", f"multi-segment connector without fill=\"none\" (d=\"{el.get('d','')[:60]}\")")

    # -- C3: dash seam on animated classes --
    seen_dash = set()
    for pts, samples, el, anc, _ in connectors:
        for cls in (el.get("class") or "").split():
            key = (cls, el.get("stroke-dasharray"))
            if key in seen_dash:
                continue
            seen_dash.add(key)
            info = classes.get(cls, {})
            anim = info.get("anim")
            if not anim or anim not in keyframes:
                continue
            dash = parse_dasharray_attr(el.get("stroke-dasharray")) or info.get("dasharray")
            if not dash:
                continue
            period = sum(dash) * (2 if len(dash) % 2 == 1 else 1)
            offset = keyframes[anim]
            if period > 0 and (offset % period) > 0.01 and abs((offset % period) - period) > 0.01:
                add("C3", f"class .{cls}: |dashoffset delta| {offset:g} is not a multiple of dasharray period {period:g}")

    # -- rect bounds (C4) --
    for r in rects:
        if r.x < -0.5 or r.y < -0.5 or r.x2 > vb_w + 0.5 or r.y2 > vb_h + 0.5:
            add("C4", f"{r.label()} outside viewBox 0 0 {vb_w:g} {vb_h:g}")
    for el, anc in nodes_all:
        if tag(el) == "text" and not in_defs(anc):
            try:
                tx, ty = float(el.get("x", 0)), float(el.get("y", 0))
            except (TypeError, ValueError):
                continue
            if tx < 0 or ty < 0 or tx > vb_w or ty > vb_h:
                add("C4", f"text anchor ({tx:g},{ty:g}) outside viewBox")

    # -- C5 / C8: traveling dots --
    conn_samples = [s for pts, s, el, anc, u in connectors if not u]
    motion_ids = set()
    motions = []
    for el, anc in nodes_all:
        if tag(el) == "animateMotion":
            if el.get("id"):
                motion_ids.add(el.get("id"))
            motions.append((el, anc))
    for el, anc in motions:
        mpts, ok = parse_path(el.get("path", ""))
        if not ok or len(mpts) < 2:
            if not ok:
                add("C5", f"animateMotion path uses unsupported commands: {el.get('path','')[:60]}")
            continue
        for arc, px, py in sample_polyline(mpts):
            near = any(
                seg_point_dist(px, py, ax, ay, bx, by) <= ON_LINE_TOL
                for s in conn_samples
                for (_, ax, ay), (_, bx, by) in zip(s, s[1:]))
            if not near:
                add("C5", f"dot at ({px:g},{py:g}) rides off every connector (path=\"{el.get('path','')[:60]}\")")
                break
        begin = el.get("begin") or ""
        for ref in re.findall(r"([\w-]+)\.(?:end|begin)", begin):
            if ref not in motion_ids:
                add("C8", f"begin=\"{begin}\" references missing id \"{ref}\"")

    # -- C10: animation presence & dot budget --
    # A structurally perfect file whose animation layer was stripped (or never
    # emitted) is still a failed glowmotion deliverable. Trails (class "trail")
    # are garnish and don't count toward the dot budget; the legend's static
    # swatch circle carries no class and is ignored.
    animated_conn = 0
    for pts, samples, el, anc, _ in connectors:
        for cls in (el.get("class") or "").split():
            if classes.get(cls, {}).get("anim") in keyframes:
                animated_conn += 1
                break
    if connectors and animated_conn == 0:
        add("C10", "no connector carries an animated dash class that resolves "
                   "to @keyframes — the flow layer is static")
    main_dots = sum(1 for el, anc in nodes_all
                    if tag(el) == "circle"
                    and "dot" in (el.get("class") or "").split())
    if main_dots == 0:
        add("C10", "no traveling dot (circle.dot with animateMotion) — every "
                   "glowmotion diagram carries at least one journey")
    elif main_dots > 8:
        add("C10", f"{main_dots} main dots (>8): dots mark informative paths, "
                   f"not every edge — trim the journeys")

    return violations


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv
    report = {}
    for f in args:
        try:
            report[f] = check_file(f)
        except Exception as e:  # checker bug must be visible, not a silent pass
            report[f] = [{"code": "CHECKER-ERROR", "msg": repr(e)}]
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        total_bad = 0
        for f, vs in report.items():
            status = "FAIL" if vs else "PASS"
            total_bad += bool(vs)
            print(f"{status}  {f}  ({len(vs)} violation{'s' if len(vs) != 1 else ''})")
            for v in vs:
                print(f"      [{v['code']}] {v['msg']}")
        print(f"\n{total_bad}/{len(report)} files with >=1 violation")


if __name__ == "__main__":
    main()

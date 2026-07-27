#!/usr/bin/env python3
"""
codegraph overview — collapse a file graph into a readable architecture diagram.

This is the glowmotion half of the artifact: instead of thousands of file dots,
it produces 8-14 module boxes on architectural tiers, with orthogonal routes and
a primary journey — the kind of picture a human can absorb in five seconds.

The difference from glowmotion: nothing here is hand-authored. Tiers, boxes,
edge weights and the journey are all DERIVED from the deterministic scan, so the
overview cannot drift from the real code.

Design contract:
  * stdlib only, no network, deterministic (same graph -> identical geometry).
  * Pure geometry + semantics; the HTML/SVG is emitted by the viewer.
  * Never invents a module or an edge that the scan did not find.

Used by render.py; also runnable standalone for inspection:
    python3 overview.py .codegraph/graph.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter, defaultdict

# Architectural reading order, top to bottom. Mirrors scan.py's LAYER_ORDER but
# drops the layers that add noise to a high-level picture (tests/docs).
TIER_ORDER = ["entry", "ui", "api", "service", "data", "util", "config", "infra"]
TIER_LABELS = {
    "entry": "Entry", "ui": "UI", "api": "API", "service": "Logic",
    "data": "Data", "util": "Shared", "config": "Config", "infra": "Infra",
    "test": "Tests", "docs": "Docs", "other": "Other",
}
OMIT_LAYERS = {"test", "docs"}

# Box geometry, in the same user units the viewer's SVG viewBox uses.
BOX_W, BOX_H = 168, 62
GAP_X, GAP_Y = 40, 96
PAD = 40          # leaves room for the band label drawn above each row


def _short(path: str) -> str:
    """A module label a human recognises: last one or two path segments."""
    if path in (".", ""):
        return "(root)"
    parts = [p for p in path.split("/") if p]
    if len(parts) <= 2:
        return "/".join(parts)
    return ".../" + "/".join(parts[-2:])


def collapse(graph, max_boxes=14):
    """Group file nodes into module boxes, keeping the most significant ones."""
    nodes = graph.get("nodes") or []
    by_id = {n["id"]: n for n in nodes}

    files = [n for n in nodes
             if n.get("type") in ("file", "config", "document") and n.get("filePath")]
    if not files:
        return [], [], {}

    # Aggregate every file into its owning directory.
    mods = {}
    for n in files:
        layer = n.get("layer") or "other"
        mod = n.get("module") or ("mod:" + (os.path.dirname(n["filePath"]) or "."))
        m = mods.get(mod)
        if not m:
            m = mods[mod] = {
                "id": mod, "path": mod[4:] if mod.startswith("mod:") else mod,
                "files": [], "loc": 0, "importance": 0.0,
                "layers": Counter(), "langs": Counter(),
                "entries": 0, "code": 0, "summary": "", "tags": [],
            }
        if n.get("type") == "file":        # real source, not config/doc
            m["code"] += 1
        m["files"].append(n["id"])
        m["loc"] += n.get("loc") or 0
        m["importance"] += n.get("importance") or 0.0
        m["layers"][layer] += 1
        if n.get("language"):
            m["langs"][n["language"]] += 1
        if n.get("isEntry"):
            m["entries"] += 1

    for m in mods.values():
        m["layer"] = m["layers"].most_common(1)[0][0]
        m["fileCount"] = len(m["files"])
        m["label"] = _short(m["path"])
        # Borrow the best summary among the module's files, preferring the
        # most important one the agent actually described.
        best, best_imp = "", -1.0
        for fid in m["files"]:
            f = by_id.get(fid) or {}
            if f.get("summary") and (f.get("importance") or 0) > best_imp:
                best, best_imp = f["summary"], f.get("importance") or 0
        m["summary"] = best
        tags = Counter()
        for fid in m["files"]:
            for t in (by_id.get(fid) or {}).get("tags") or []:
                tags[t] += 1
        m["tags"] = [t for t, _ in tags.most_common(3)]

    # Rank and keep the modules worth showing; the rest are omitted (the explore
    # view still has every file, so nothing is lost — only summarized away).
    ranked = sorted(mods.values(),
                    key=lambda m: (-(m["importance"] + m["entries"] * 0.5), -m["loc"], m["path"]))
    candidates = [m for m in ranked if m["layer"] not in OMIT_LAYERS]

    # Drop scaffolding-only modules: a directory holding nothing but config or
    # docs (a lone package.json) is not architecture. Note this is about KIND,
    # not size — a small module of real code (a package's public __init__) stays.
    def worth_showing(m):
        if m["entries"]:
            return True
        if not m["code"]:                 # no source files at all
            return False
        return m["importance"] > 0.02 or (m["fileCount"] >= 2 and m["loc"] >= 20)

    filtered = [m for m in candidates if worth_showing(m)]
    visible = (filtered or candidates)[:max_boxes]
    if not visible:
        visible = ranked[:max_boxes]
    keep = {m["id"] for m in visible}

    # Map every file to its visible module (or None when its module was dropped).
    file_to_box = {}
    for m in mods.values():
        target = m["id"] if m["id"] in keep else None
        for fid in m["files"]:
            file_to_box[fid] = target

    # Aggregate file-level imports into module-level edges.
    weights = Counter()
    for e in graph.get("edges") or []:
        if e.get("type") not in ("imports", "calls"):
            continue
        a = file_to_box.get(e.get("source"))
        b = file_to_box.get(e.get("target"))
        # calls may originate from a symbol; resolve through its parent file.
        if a is None:
            sa = by_id.get(e.get("source")) or {}
            a = file_to_box.get("file:" + sa.get("filePath", "")) if sa.get("filePath") else None
        if b is None:
            sb = by_id.get(e.get("target")) or {}
            b = file_to_box.get("file:" + sb.get("filePath", "")) if sb.get("filePath") else None
        if not a or not b or a == b:
            continue
        weights[(a, b)] += 1

    # Cap the connector count. A dense module graph is near-complete, and drawing
    # every link recreates the hairball the overview exists to avoid. Keep the
    # heaviest links, but guarantee every box keeps its single strongest tie so
    # nothing is left visually orphaned.
    ranked_edges = sorted(weights.items(), key=lambda kv: (-kv[1], kv[0]))
    budget = max(18, min(46, len(visible) * 3))
    kept = dict(ranked_edges[:budget])
    connected = {n for pair in kept for n in pair}
    for (a, b), w in ranked_edges:
        if len(kept) >= budget + len(visible):
            break
        if a not in connected or b not in connected:
            kept[(a, b)] = w
            connected.update((a, b))

    edges = [{"from": a, "to": b, "weight": w} for (a, b), w in kept.items()]
    return visible, edges, file_to_box


def assign_tiers(boxes, edges):
    """Place boxes on rows: architectural layer first, longest-path as tiebreak."""
    present = [t for t in TIER_ORDER if any(b["layer"] == t for b in boxes)]
    extra = sorted({b["layer"] for b in boxes} - set(present))
    order = present + extra
    row_of = {t: i for i, t in enumerate(order)}
    for b in boxes:
        b["tier"] = row_of.get(b["layer"], len(order))
    return order


MAX_COLS = 4          # wrap wide tiers so the diagram stays landscape


def layout(boxes, edges, tier_order):
    """Deterministic row packing + orthogonal routing. Returns (geometry, size)."""
    grouped = defaultdict(list)
    for b in boxes:
        grouped[b["tier"]].append(b)

    # A tier holding one box would waste a whole row, so adjacent single-box
    # tiers share a row; wide tiers wrap at MAX_COLS. Reading order is kept.
    rows, row_tiers = [], []
    for tier in sorted(grouped):
        members = sorted(grouped[tier], key=lambda b: (-b["importance"], b["path"]))
        # Merge a lone box onto the previous row only if that row is also sparse;
        # append (never prepend) so left-to-right still follows tier order.
        if (len(members) == 1 and rows and len(rows[-1]) < MAX_COLS
                and len(row_tiers[-1]) < 3 and len(rows[-1]) <= 2):
            rows[-1].extend(members)
            row_tiers[-1].append(tier)
            continue
        for i in range(0, len(members), MAX_COLS):
            rows.append(members[i:i + MAX_COLS])
            row_tiers.append([tier])

    max_cols = max((len(r) for r in rows), default=1)
    width = PAD * 2 + max_cols * BOX_W + (max_cols - 1) * GAP_X
    height = PAD * 2 + len(rows) * BOX_H + max(0, len(rows) - 1) * GAP_Y

    for ri, row in enumerate(rows):
        # Within a merged row, keep tier order left-to-right so the eye still
        # travels entry -> ui -> api rather than jumping by size.
        row.sort(key=lambda b: (b["tier"], -b["importance"], b["path"]))
        n = len(row)
        span = n * BOX_W + (n - 1) * GAP_X
        x0 = (width - span) / 2
        y = PAD + ri * (BOX_H + GAP_Y)
        for ci, b in enumerate(row):
            b["x"] = round(x0 + ci * (BOX_W + GAP_X), 1)
            b["y"] = round(y, 1)
            b["w"], b["h"] = BOX_W, BOX_H
            b["row"], b["col"] = ri, ci

    pos = {b["id"]: b for b in boxes}
    for e in edges:
        a, b = pos.get(e["from"]), pos.get(e["to"])
        if not a or not b:
            e["d"] = ""
            continue
        e["d"] = route(a, b)
        e["down"] = b["y"] > a["y"]
    # Row labels come from whichever tiers landed on each row.
    labels = [[t for t in ts] for ts in row_tiers]
    return width, round(height), labels


def route(a, b):
    """Orthogonal path between two boxes, leaving each from the nearer face.

    Downward edges exit the bottom and enter the top with a mid-way jog, which
    keeps them clear of the boxes in between (the C2 rule glowmotion enforces).
    Same-row and upward edges bow out to the side instead of cutting through.
    """
    ax, ay = a["x"] + a["w"] / 2, a["y"]
    bx, by = b["x"] + b["w"] / 2, b["y"]

    if by > ay:                                   # downward: bottom -> top
        y1 = a["y"] + a["h"]
        y2 = b["y"]
        if abs(bx - ax) < 1:
            return "M%.1f %.1f L%.1f %.1f" % (ax, y1, bx, y2)
        mid = (y1 + y2) / 2
        return "M%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f" % (
            ax, y1, ax, mid, bx, mid, bx, y2)

    if abs(by - ay) < 1:                          # same row: side to side
        if bx > ax:
            x1, x2 = a["x"] + a["w"], b["x"]
        else:
            x1, x2 = a["x"], b["x"] + b["w"]
        y = ay + a["h"] / 2
        return "M%.1f %.1f L%.1f %.1f" % (x1, y, x2, y)

    # upward (feedback): leave the side, climb clear of the rows, re-enter bottom
    out = a["x"] + a["w"] + 22 if bx >= ax else a["x"] - 22
    y1 = ay + a["h"] / 2
    y2 = b["y"] + b["h"]
    return "M%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f" % (
        (a["x"] + a["w"] if bx >= ax else a["x"]), y1, out, y1, out, y2, bx, y2)


def primary_journey(boxes, edges, limit=6):
    """The longest high-traffic downward path — the story the diagram tells.

    Depth-first over downward edges only (so it always reads top-to-bottom),
    preferring heavier edges. This is the animated route.
    """
    if not boxes:
        return []
    pos = {b["id"]: b for b in boxes}
    out = defaultdict(list)
    for e in edges:
        a, b = pos.get(e["from"]), pos.get(e["to"])
        if a and b and b["y"] > a["y"]:
            out[e["from"]].append((e["weight"], e["to"]))
    for k in out:
        out[k].sort(reverse=True)

    best = []

    def walk(node, path, seen):
        nonlocal best
        if len(path) > len(best):
            best = list(path)
        if len(path) >= limit:
            return
        for _, nxt in out.get(node, [])[:3]:
            if nxt in seen:
                continue
            seen.add(nxt)
            path.append(nxt)
            walk(nxt, path, seen)
            path.pop()
            seen.discard(nxt)

    # Start from the topmost, most important boxes.
    starts = sorted(boxes, key=lambda b: (b["row"], -b["importance"]))[:4]
    for s in starts:
        walk(s["id"], [s["id"]], {s["id"]})
        if len(best) >= limit:
            break

    # A flat project (everything on one row) still deserves a journey: fall back
    # to the heaviest same-row chain so the diagram is never motionless.
    if len(best) < 2:
        flat = sorted(edges, key=lambda e: -e["weight"])
        if flat:
            best = [flat[0]["from"], flat[0]["to"]]
            nxt = {e["from"]: e["to"] for e in flat}
            seen = set(best)
            while len(best) < limit and best[-1] in nxt and nxt[best[-1]] not in seen:
                best.append(nxt[best[-1]])
                seen.add(best[-1])

    hops = [[best[i], best[i + 1]] for i in range(len(best) - 1)]
    return hops


def starmap(graph, boxes, file_to_box):
    """Galaxy layout:每个模块是一个星系，文件是星，重要度决定亮度与大小。

    与 box 视图互补 —— box 讲"架构分层"，星图讲"质量分布"：
    哪些模块是巨大的恒星形成区，哪些只是稀疏的尘埃。

    Deterministic: 角度与半径全部由 id hash 与排名决定，无随机。
    """
    nodes = graph.get("nodes") or []
    by_mod = defaultdict(list)
    for n in nodes:
        if n.get("type") not in ("file", "config", "document"):
            continue
        box = file_to_box.get(n["id"])
        if box:
            by_mod[box].append(n)

    W = H = 1000.0
    cx, cy = W / 2, H / 2
    order = sorted(boxes, key=lambda b: -(b["importance"] + b["loc"] / 5000.0))

    galaxies, stars = [], []
    n_gal = max(1, len(order))
    for gi, b in enumerate(order):
        # 黄金角螺旋：星系彼此不重叠，且中心密、外围疏
        t = (gi + 0.5) / n_gal
        ang = gi * 2.39996                      # golden angle, rad
        rad = (0.13 + 0.80 * math.sqrt(t)) * (W * 0.46)
        gx, gy = cx + math.cos(ang) * rad, cy + math.sin(ang) * rad
        # z gives the disc real thickness so tilting the camera reveals depth.
        # Important modules sit near the galactic plane; peripheral ones drift out.
        gz = (hash_f(b["id"] + "z") - 0.5) * 190 * (1.0 - 0.55 * (1.0 - t))
        members = sorted(by_mod.get(b["id"], []),
                         key=lambda n: -(n.get("importance") or 0))
        # 星系半径随成员数增长，但收敛（sqrt）以免大模块吞掉画面
        gr = 26 + min(78, math.sqrt(max(1, len(members))) * 15)
        galaxies.append({
            "id": b["id"], "label": b["label"], "layer": b["layer"],
            "x": round(gx, 1), "y": round(gy, 1), "z": round(gz, 1),
            "r": round(gr, 1),
            "files": len(members), "loc": b["loc"],
            "summary": b.get("summary", ""),
        })
        for si, n in enumerate(members[:60]):
            st = (si + 0.5) / max(1, min(len(members), 60))
            sang = si * 2.39996 + hash_f(n["id"]) * 6.283
            srad = math.sqrt(st) * gr * 0.92
            imp = n.get("importance") or 0
            loc = n.get("loc") or 1
            # Stars scatter around their galaxy's plane; brighter ones hug it,
            # so tilting keeps the important stars readable instead of scattered.
            sz = gz + (hash_f(n["id"] + "z") - 0.5) * gr * 0.85 * (1.25 - imp)
            stars.append({
                "id": n["id"], "name": n["name"], "mod": b["id"],
                "x": round(gx + math.cos(sang) * srad, 1),
                "y": round(gy + math.sin(sang) * srad, 1),
                "z": round(sz, 1),
                # 视星等。不做线性截断——那会让 top 文件全部饱和成 1.00，
                # 失去区分度。用平方根压缩保留高端差异。
                "mag": round(min(1.0, math.sqrt(
                    min(1.0, imp * 1.1 + min(loc / 2600.0, 0.30)))), 3),
                "layer": n.get("layer") or "other",
                "loc": loc,
            })

    # 星系之间的"光丝"：模块级依赖，权重决定亮度
    pos = {g["id"]: g for g in galaxies}
    links = []
    for e in _module_edges(graph, file_to_box):
        a, b2 = pos.get(e["from"]), pos.get(e["to"])
        if not a or not b2:
            continue
        links.append({"from": e["from"], "to": e["to"], "weight": e["weight"]})
    links.sort(key=lambda l: -l["weight"])
    return {"width": W, "height": H, "galaxies": galaxies,
            "stars": stars, "links": links[:70]}


def hash_f(s):
    """Deterministic 0..1 from a string (same FNV-1a the viewer uses)."""
    h = 2166136261
    for ch in s:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h / 4294967295.0


def _module_edges(graph, file_to_box):
    """Module-level import/call weights, shared by both overview layouts."""
    by_id = {n["id"]: n for n in graph.get("nodes") or []}
    w = Counter()
    for e in graph.get("edges") or []:
        if e.get("type") not in ("imports", "calls"):
            continue
        a = file_to_box.get(e.get("source"))
        b = file_to_box.get(e.get("target"))
        if a is None:
            s = by_id.get(e.get("source")) or {}
            a = file_to_box.get("file:" + s.get("filePath", "")) if s.get("filePath") else None
        if b is None:
            t = by_id.get(e.get("target")) or {}
            b = file_to_box.get("file:" + t.get("filePath", "")) if t.get("filePath") else None
        if a and b and a != b:
            w[(a, b)] += 1
    return [{"from": a, "to": b, "weight": c} for (a, b), c in w.items()]


def build(graph, max_boxes=14):
    """Return the overview payload the viewer renders as SVG."""
    boxes, edges, file_to_box = collapse(graph, max_boxes)
    if not boxes:
        return None
    tier_order = assign_tiers(boxes, edges)
    width, height, row_labels = layout(boxes, edges, tier_order)
    hops = primary_journey(boxes, edges)

    # Keep only what the viewer needs; drop the file id lists (they can be large).
    lean = []
    for b in boxes:
        lean.append({
            "id": b["id"], "label": b["label"], "path": b["path"],
            "layer": b["layer"], "tier": b["tier"], "row": b["row"],
            "x": b["x"], "y": b["y"], "w": b["w"], "h": b["h"],
            "loc": b["loc"], "fileCount": b["fileCount"],
            "entries": b["entries"], "summary": b["summary"], "tags": b["tags"],
            "lang": (b["langs"].most_common(1)[0][0] if b["langs"] else ""),
        })
    # One label per rendered row, joined when tiers were merged onto one row.
    # row_labels holds tier *indices*; map them back to layer ids.
    rows = []
    for ri, tier_idxs in enumerate(row_labels):
        names = [tier_order[i] if i < len(tier_order) else "other" for i in tier_idxs]
        y = min((b["y"] for b in boxes if b["row"] == ri), default=0)
        rows.append({
            "row": ri, "y": y,
            "label": " · ".join(TIER_LABELS.get(t, t.title()) for t in names),
            "layer": names[0],
        })
    return {
        "width": width, "height": height,
        "rows": rows,
        "boxes": lean,
        "edges": [e for e in edges if e.get("d")],
        "journey": hops,
        # Second, complementary reading of the same data: mass and clustering
        # instead of layering. Cheap to compute, so both ship in one artifact.
        "starmap": starmap(graph, boxes, file_to_box),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="overview.py",
        description="Collapse graph.json into an architecture overview (codegraph)")
    ap.add_argument("graph", help="path to graph.json")
    ap.add_argument("--max-boxes", type=int, default=14)
    args = ap.parse_args(argv)

    with open(args.graph, "r", encoding="utf-8") as fh:
        graph = json.load(fh)
    ov = build(graph, args.max_boxes)
    if not ov:
        print("error: no file nodes to summarize", file=sys.stderr)
        return 1
    print(json.dumps(ov, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

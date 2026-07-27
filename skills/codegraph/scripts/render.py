#!/usr/bin/env python3
"""
codegraph render — graph.json (+ optional enrich.json) -> ONE self-contained HTML.

Stage 3 of 3 in the codegraph pipeline:

    scan.py   ->  graph.json + digest.md      (deterministic structure)
    agent     ->  enrich.json                 (semantic summaries / layers / tours)
    render.py ->  codegraph.html              (this file)

Design contract:
  * ZERO third-party dependencies (stdlib only) and ZERO CDN/network calls at view time.
  * Validate BEFORE writing. A broken artifact never replaces a good one:
    we render to a temp file in the same directory and atomically os.replace().
  * The output is one portable file you can commit, email, or open offline.

Usage:
    python3 render.py [--in .codegraph] [--enrich .codegraph/enrich.json]
                      [-o .codegraph/codegraph.html] [--title TEXT] [--open]
    python3 render.py --validate-only --in .codegraph
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import overview  # noqa: E402  (sibling module, stdlib-only)

# --------------------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------------------

REQUIRED_TOP = ("version", "project", "nodes", "edges")


def validate_graph(graph):
    """Return (errors, warnings). Errors block delivery; warnings are informational."""
    errors, warnings = [], []

    if not isinstance(graph, dict):
        return ["graph.json is not a JSON object"], []
    for key in REQUIRED_TOP:
        if key not in graph:
            errors.append("missing required top-level key: %r" % key)
    if errors:
        return errors, warnings

    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    if not isinstance(nodes, list) or not nodes:
        errors.append("nodes must be a non-empty list")
        return errors, warnings
    if not isinstance(edges, list):
        errors.append("edges must be a list")
        return errors, warnings

    ids = {}
    for i, n in enumerate(nodes):
        if not isinstance(n, dict):
            errors.append("nodes[%d] is not an object" % i)
            continue
        nid = n.get("id")
        if not nid or not isinstance(nid, str):
            errors.append("nodes[%d] has no valid string id" % i)
            continue
        if nid in ids:
            errors.append("duplicate node id: %r" % nid)
        ids[nid] = True
        if not n.get("name"):
            warnings.append("node %r has no name" % nid)

    dangling = 0
    for e in edges:
        if not isinstance(e, dict):
            errors.append("an edge is not an object")
            break
        s, t = e.get("source"), e.get("target")
        if s not in ids or t not in ids:
            dangling += 1
    if dangling:
        errors.append("%d edge(s) reference unknown node ids" % dangling)

    if not graph.get("layers"):
        warnings.append("no layers present; layer filter will be empty")
    return errors, warnings


def validate_enrich(enrich, node_ids):
    """Enrichment is advisory: unknown ids are dropped with a warning, never fatal."""
    warnings = []
    if not isinstance(enrich, dict):
        return {}, ["enrich.json is not an object; ignored"]

    clean = {"project": {}, "nodes": {}, "layers": {}, "tours": []}

    proj = enrich.get("project")
    if isinstance(proj, dict):
        clean["project"] = {k: v for k, v in proj.items() if isinstance(v, str)}

    nodes = enrich.get("nodes")
    if isinstance(nodes, dict):
        unknown = 0
        for nid, payload in nodes.items():
            if nid not in node_ids:
                unknown += 1
                continue
            if isinstance(payload, str):
                clean["nodes"][nid] = {"summary": payload}
            elif isinstance(payload, dict):
                clean["nodes"][nid] = payload
        if unknown:
            warnings.append("enrich.nodes: dropped %d entry(ies) with unknown node ids" % unknown)

    layers = enrich.get("layers")
    if isinstance(layers, dict):
        clean["layers"] = {k: v for k, v in layers.items() if isinstance(v, str)}

    tours = enrich.get("tours") or enrich.get("tour")
    if isinstance(tours, list):
        for t in tours:
            if not isinstance(t, dict):
                continue
            steps = []
            for st in (t.get("steps") or []):
                if isinstance(st, str):
                    nid, note = st, ""
                elif isinstance(st, dict):
                    nid, note = st.get("nodeId") or st.get("id"), st.get("note", "")
                else:
                    continue
                if nid in node_ids:
                    steps.append({"nodeId": nid, "note": note})
            if steps:
                clean["tours"].append({
                    "title": t.get("title") or "Tour",
                    "description": t.get("description", ""),
                    "steps": steps,
                })
            elif t.get("title"):
                warnings.append("tour %r dropped: no steps matched known node ids" % t["title"])
    return clean, warnings


def merge(graph, enrich):
    """Fold enrichment into the graph. Structure always wins; semantics fill the gaps."""
    if enrich.get("project", {}).get("description"):
        graph["project"]["description"] = enrich["project"]["description"]

    by_id = {n["id"]: n for n in graph["nodes"]}
    enriched_count = 0
    # A node with no agent summary still deserves words: fall back to the file's
    # own docstring so the inspector is never just numbers.
    doc_count = 0
    for node in graph["nodes"]:
        if not node.get("summary") and node.get("doc"):
            node["summary"] = node["doc"]
            node["summarySource"] = "docstring"
            doc_count += 1
    graph["docSummaries"] = doc_count
    for nid, payload in enrich.get("nodes", {}).items():
        node = by_id.get(nid)
        if not node:
            continue
        if payload.get("summary"):
            # The agent's words win over the extracted docstring.
            node["summary"] = payload["summary"]
            node["summarySource"] = "agent"
            enriched_count += 1
        if payload.get("layer"):
            node["layer"] = payload["layer"]
        tags = payload.get("tags")
        if isinstance(tags, list):
            node["tags"] = [str(t) for t in tags][:8]

    for layer in graph.get("layers", []):
        desc = enrich.get("layers", {}).get(layer["id"])
        if desc:
            layer["description"] = desc

    if enrich.get("tours"):
        graph["tour"] = enrich["tours"]
    graph["enrichedNodes"] = enriched_count
    return graph


def slim(graph):
    """Strip fields the viewer never reads, so the HTML stays small."""
    keep_node = {
        "id", "type", "name", "filePath", "module", "language", "layer", "loc",
        "fanIn", "fanOut", "importance", "isEntry", "defCount", "routes",
        "httpVerbs", "title", "summary", "tags", "lineRange", "kind",
        "fileCount", "languages", "usedBy", "importCount", "doc", "symbols",
        "summarySource", "parent", "depth", "ownFiles",
    }
    out = dict(graph)
    out["nodes"] = [{k: v for k, v in n.items() if k in keep_node and v not in ("", [], None)}
                    for n in graph["nodes"]]
    out["edges"] = [{k: v for k, v in e.items() if k in ("source", "target", "type", "line")}
                    for e in graph["edges"]]
    if "stats" in out:
        out["stats"] = {k: v for k, v in out["stats"].items() if k != "elapsed_sec"}
    return out


# --------------------------------------------------------------------------------------
# HTML template (viewer.html, loaded from disk so styling stays editable as real markup)
# --------------------------------------------------------------------------------------

VIEWER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "viewer.html")


def load_template():
    """Read the viewer shell. Kept as a separate file so CSS/JS edits are plain markup."""
    try:
        with open(VIEWER_PATH, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:
        raise RuntimeError("cannot read viewer template at %s: %s" % (VIEWER_PATH, exc))



# --------------------------------------------------------------------------------------
# Render + atomic delivery
# --------------------------------------------------------------------------------------

def render_html(graph, title, max_boxes=14):
    data = slim(graph)
    # The overview is derived from the FULL graph (before slimming drops fields
    # it needs), then embedded alongside it as a second, coarser view.
    try:
        data["overview"] = overview.build(graph, max_boxes)
    except Exception as exc:                     # never let the extra view block delivery
        print("  warning: overview generation failed (%s); explore view only" % exc)
        data["overview"] = None
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    # Never let the payload terminate the host <script> element.
    payload = payload.replace("</", "<\\/")
    html = load_template().replace("__DATA__", payload)
    return html.replace("__TITLE__", title)


def deliver(html, out_path):
    """Write to a temp file in the SAME directory, then atomically replace the target."""
    out_dir = os.path.dirname(os.path.abspath(out_path)) or "."
    os.makedirs(out_dir, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=out_dir, prefix=".codegraph-", suffix=".html")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(html)
        if "__DATA__" in html or "__TITLE__" in html:
            raise ValueError("template placeholders left unfilled")
        os.replace(tmp, out_path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return out_path


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="render.py",
        description="Render graph.json (+enrich.json) into one self-contained HTML (codegraph stage 3)")
    ap.add_argument("--in", dest="indir", default=".codegraph",
                    help="directory containing graph.json (default: .codegraph)")
    ap.add_argument("--graph", help="explicit path to graph.json (overrides --in)")
    ap.add_argument("--enrich", help="path to enrich.json (default: <indir>/enrich.json if present)")
    ap.add_argument("-o", "--out", help="output HTML (default: <indir>/codegraph.html)")
    ap.add_argument("--title", help="title shown in the artifact (default: project name)")
    ap.add_argument("--max-boxes", type=int, default=14,
                    help="module boxes in the overview diagram (default: 14)")
    ap.add_argument("--validate-only", action="store_true", help="validate inputs, write nothing")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--open", dest="do_open", action="store_true", help="open the result in a browser")
    args = ap.parse_args(argv)

    gpath = args.graph or os.path.join(args.indir, "graph.json")
    if not os.path.isfile(gpath):
        print("error: graph.json not found at %s\n       run scan.py first." % gpath, file=sys.stderr)
        return 2
    try:
        with open(gpath, "r", encoding="utf-8") as fh:
            graph = json.load(fh)
    except (OSError, ValueError) as exc:
        print("error: cannot read %s: %s" % (gpath, exc), file=sys.stderr)
        return 2

    errors, warnings = validate_graph(graph)
    if errors:
        print("VALIDATION FAILED (%d error(s)) — nothing was written:" % len(errors), file=sys.stderr)
        for e in errors[:20]:
            print("  - " + e, file=sys.stderr)
        return 1

    epath = args.enrich or os.path.join(os.path.dirname(gpath) or ".", "enrich.json")
    enriched = 0
    if os.path.isfile(epath):
        try:
            with open(epath, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            clean, ew = validate_enrich(raw, {n["id"] for n in graph["nodes"]})
            warnings.extend(ew)
            graph = merge(graph, clean)
            enriched = graph.get("enrichedNodes", 0)
        except ValueError as exc:
            warnings.append("enrich.json is not valid JSON (%s); rendered without it" % exc)
    else:
        warnings.append("no enrich.json found; rendering structure only (no AI summaries/tours)")

    for w in warnings[:20]:
        print("  warning: " + w)
    if args.strict and warnings:
        print("error: --strict and %d warning(s)" % len(warnings), file=sys.stderr)
        return 1

    if args.validate_only:
        print("OK: %d nodes, %d edges, %d enriched, %d tour(s)" % (
            len(graph["nodes"]), len(graph["edges"]), enriched, len(graph.get("tour") or [])))
        return 0

    out = args.out or os.path.join(os.path.dirname(gpath) or ".", "codegraph.html")
    title = args.title or graph.get("project", {}).get("name") or "codebase"
    html = render_html(graph, title, args.max_boxes)
    deliver(html, out)

    ov = overview.build(graph, args.max_boxes)
    size_kb = os.path.getsize(out) / 1024.0
    print("codegraph artifact ready")
    print("  nodes    : %d   edges: %d" % (len(graph["nodes"]), len(graph["edges"])))
    if ov:
        print("  overview : %d modules, %d links, %d-hop journey" % (
            len(ov["boxes"]), len(ov["edges"]), len(ov["journey"])))
    docs = graph.get("docSummaries", 0)
    described = sum(1 for n in graph["nodes"]
                    if n.get("type") in ("file", "config", "document") and n.get("summary"))
    total_files = sum(1 for n in graph["nodes"]
                      if n.get("type") in ("file", "config", "document"))
    from_doc = sum(1 for n in graph["nodes"] if n.get("summarySource") == "docstring")
    from_agent = sum(1 for n in graph["nodes"] if n.get("summarySource") == "agent")
    print("  described: %d/%d files have a summary (%d%%) — %d from docstrings, %d from the agent"
          % (described, total_files,
             round(100 * described / total_files) if total_files else 0,
             from_doc, from_agent))
    print("  tours    : %d" % len(graph.get("tour") or []))
    print("  output   : %s (%.0f KB, self-contained)" % (out, size_kb))
    if args.do_open:
        webbrowser.open("file://" + os.path.abspath(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

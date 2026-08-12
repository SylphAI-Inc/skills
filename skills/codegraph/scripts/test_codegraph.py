#!/usr/bin/env python3
"""
Regression tests for the codegraph pipeline. Stdlib only (unittest).

Run:
    python3 test_codegraph.py           # quiet
    python3 test_codegraph.py -v        # verbose
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import scan      # noqa: E402
import render    # noqa: E402
import overview  # noqa: E402


# --------------------------------------------------------------------------------------
# Fixture: a tiny polyglot repo with known structure, one cycle, and a clear entry point.
# --------------------------------------------------------------------------------------

FIXTURE = {
    "src/main.py": (
        "import os\n"
        "from src.services.auth import login\n"
        "from src.models.user import User\n"
        "import requests\n"
        "\n"
        "def main():\n"
        "    u = User('a')\n"
        "    return login(u)\n"
    ),
    "src/services/auth.py": (
        '"""Authentication service: verifies credentials and issues sessions."""\n'
        "from src.models.user import User\n"
        "from src.utils.hashing import hash_password\n"
        "\n"
        "def login(user):\n"
        "    return hash_password(user.name)\n"
        "\n"
        "class AuthService:\n"
        "    def authenticate(self):\n"
        "        return True\n"
    ),
    "src/models/user.py": (
        "from src.utils.hashing import hash_password\n"
        "\n"
        "class User:\n"
        "    def __init__(self, name):\n"
        "        self.name = name\n"
    ),
    "src/utils/hashing.py": (
        '"""Password hashing helpers shared by every auth path."""\n'
        "import hashlib\n"
        "\n"
        "def hash_password(pw):\n"
        "    return hashlib.sha256(pw.encode()).hexdigest()\n"
    ),
    # Deliberate 2-file import cycle for SCC detection.
    "src/cycle_a.py": "from src.cycle_b import beta\n\ndef alpha():\n    return beta()\n",
    "src/cycle_b.py": "from src.cycle_a import alpha\n\ndef beta():\n    return 1\n",
    "web/app.ts": (
        "import { helper } from './helper';\n"
        "import express from 'express';\n"
        "\n"
        "export const router = express.Router();\n"
        "router.get('/users', (req, res) => res.json(helper()));\n"
        "\n"
        "export class Controller {\n"
        "  handle() { return helper(); }\n"
        "}\n"
    ),
    "web/helper.ts": ("/**\n * Returns the canonical answer.\n */\n"
                      "export function helper() {\n  return 42;\n}\n"),
    "cmd/server/main.go": (
        "package main\n"
        "\n"
        "import (\n"
        '\t"fmt"\n'
        '\t"github.com/example/proj/internal/store"\n'
        ")\n"
        "\n"
        "func main() {\n"
        "\tfmt.Println(store.Get())\n"
        "}\n"
    ),
    "internal/store/store.go": (
        "package store\n"
        "\n"
        "type Store struct{ n int }\n"
        "\n"
        "func Get() int { return 1 }\n"
    ),
    "go.mod": "module github.com/example/proj\n\ngo 1.21\n",
    "package.json": '{"name":"fx","dependencies":{"express":"^4.0.0","react":"^18.0.0"}}\n',
    "requirements.txt": "requests==2.31.0\nflask\n",
    "README.md": "# Fixture Project\n\nA test fixture.\n",
    "tests/test_auth.py": "from src.services.auth import login\n\ndef test_login():\n    assert True\n",
    "node_modules/junk/index.js": "module.exports = 'should be ignored';\n",
    "dist/bundle.min.js": "var a=1;" * 50 + "\n",
}


def make_repo(root):
    for rel, content in FIXTURE.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="codegraph-test-")
        cls.repo = os.path.join(cls.tmp, "repo")
        os.makedirs(cls.repo)
        make_repo(cls.repo)
        cls.scanned = scan.scan(cls.repo, max_files=4000, want_calls=True, symbols_for=250)
        cls.graph = scan.build_graph(cls.scanned)
        cls.ids = {n["id"] for n in cls.graph["nodes"]}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


class TestDiscovery(Base):
    def test_finds_source_files(self):
        self.assertIn("file:src/main.py", self.ids)
        self.assertIn("file:web/app.ts", self.ids)
        self.assertIn("file:cmd/server/main.go", self.ids)

    def test_excludes_node_modules_and_minified(self):
        rels = set(self.scanned["files"])
        self.assertNotIn("node_modules/junk/index.js", rels)
        self.assertNotIn("dist/bundle.min.js", rels)

    def test_keeps_docs_and_config_as_context(self):
        self.assertIn("file:README.md", self.ids)
        self.assertIn("file:package.json", self.ids)

    def test_language_detection(self):
        langs = self.graph["project"]["languages"]
        for expected in ("python", "typescript", "go"):
            self.assertIn(expected, langs)

    def test_framework_detection(self):
        fw = self.graph["project"]["frameworks"]
        self.assertIn("Express", fw)
        self.assertIn("React", fw)
        self.assertIn("Flask", fw)


class TestImportResolution(Base):
    def _has_import(self, src, dst):
        return any(e["type"] == "imports" and e["source"] == "file:" + src
                   and e["target"] == "file:" + dst for e in self.graph["edges"])

    def test_python_package_import(self):
        self.assertTrue(self._has_import("src/main.py", "src/services/auth.py"))
        self.assertTrue(self._has_import("src/main.py", "src/models/user.py"))

    def test_python_shared_dependency(self):
        self.assertTrue(self._has_import("src/services/auth.py", "src/utils/hashing.py"))
        self.assertTrue(self._has_import("src/models/user.py", "src/utils/hashing.py"))

    def test_typescript_relative_import(self):
        self.assertTrue(self._has_import("web/app.ts", "web/helper.ts"))

    def test_go_module_import(self):
        self.assertTrue(self._has_import("cmd/server/main.go", "internal/store/store.go"))

    def test_externals_recorded_not_as_files(self):
        self.assertIn("ext:requests", self.ids)
        self.assertIn("ext:express", self.ids)
        # stdlib/3rd-party must never become file nodes
        self.assertNotIn("file:requests", self.ids)

    def test_no_self_imports(self):
        for e in self.graph["edges"]:
            self.assertNotEqual(e["source"], e["target"])


class TestSymbols(Base):
    def test_extracts_python_symbols(self):
        names = {n["name"] for n in self.graph["nodes"] if n["id"].startswith("sym:")}
        for expected in ("login", "AuthService", "User", "hash_password", "main"):
            self.assertIn(expected, names)

    def test_extracts_typescript_symbols(self):
        names = {n["name"] for n in self.graph["nodes"] if n["id"].startswith("sym:")}
        self.assertIn("helper", names)
        self.assertIn("Controller", names)

    def test_extracts_go_symbols(self):
        names = {n["name"] for n in self.graph["nodes"] if n["id"].startswith("sym:")}
        self.assertIn("Store", names)

    def test_symbols_have_valid_line_ranges(self):
        for n in self.graph["nodes"]:
            if not n["id"].startswith("sym:"):
                continue
            lo, hi = n["lineRange"]
            self.assertGreaterEqual(lo, 1)
            self.assertGreaterEqual(hi, lo)

    def test_symbols_are_contained_by_their_file(self):
        contains = {(e["source"], e["target"]) for e in self.graph["edges"]
                    if e["type"] == "contains"}
        for n in self.graph["nodes"]:
            if n["id"].startswith("sym:"):
                self.assertIn(("file:" + n["filePath"], n["id"]), contains)


class TestMetrics(Base):
    def test_detects_import_cycle(self):
        flat = {nid for comp in self.graph["cycles"] for nid in comp}
        self.assertIn("file:src/cycle_a.py", flat)
        self.assertIn("file:src/cycle_b.py", flat)

    def test_shared_utility_has_highest_fan_in(self):
        hashing = next(n for n in self.graph["nodes"] if n["id"] == "file:src/utils/hashing.py")
        self.assertGreaterEqual(hashing["fanIn"], 2)

    def test_entry_point_detection(self):
        entries = {n["id"] for n in self.graph["nodes"] if n.get("isEntry")}
        self.assertTrue(
            {"file:src/main.py", "file:cmd/server/main.go"} & entries,
            "expected at least one main.* to be flagged as an entry point")

    def test_route_extraction_only_from_real_declarations(self):
        app = next(n for n in self.graph["nodes"] if n["id"] == "file:web/app.ts")
        self.assertIn("/users", app.get("routes", []))

    def test_importance_is_bounded(self):
        for n in self.graph["nodes"]:
            if "importance" in n:
                self.assertGreaterEqual(n["importance"], 0.0)
                self.assertLessEqual(n["importance"], 1.0)

    def test_layers_assigned(self):
        layer_ids = {l["id"] for l in self.graph["layers"]}
        self.assertIn("test", layer_ids)
        by_id = {n["id"]: n for n in self.graph["nodes"]}
        self.assertEqual(by_id["file:tests/test_auth.py"]["layer"], "test")

    def test_determinism(self):
        again = scan.build_graph(
            scan.scan(self.repo, max_files=4000, want_calls=True, symbols_for=250))
        self.assertEqual(
            json.dumps(self.graph["nodes"], sort_keys=True),
            json.dumps(again["nodes"], sort_keys=True))
        self.assertEqual(len(self.graph["edges"]), len(again["edges"]))


class TestGraphIntegrity(Base):
    def test_no_dangling_edges(self):
        for e in self.graph["edges"]:
            self.assertIn(e["source"], self.ids)
            self.assertIn(e["target"], self.ids)

    def test_unique_node_ids(self):
        all_ids = [n["id"] for n in self.graph["nodes"]]
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_passes_renderer_validation(self):
        errors, _ = render.validate_graph(self.graph)
        self.assertEqual(errors, [])

    def test_digest_mentions_key_facts(self):
        digest = scan.build_digest(self.scanned, self.graph)
        self.assertIn("Entry points", digest)
        self.assertIn("hashing.py", digest)
        self.assertIn("enrich.json", digest)
        self.assertIn("Dependency cycles", digest)


class TestValidation(unittest.TestCase):
    def test_rejects_missing_keys(self):
        errors, _ = render.validate_graph({"nodes": [], "edges": []})
        self.assertTrue(any("version" in e for e in errors))

    def test_rejects_dangling_edge(self):
        bad = {"version": "1", "project": {"name": "x"},
               "nodes": [{"id": "a", "name": "A"}],
               "edges": [{"source": "a", "target": "ghost", "type": "imports"}]}
        errors, _ = render.validate_graph(bad)
        self.assertTrue(any("unknown node ids" in e for e in errors))

    def test_rejects_duplicate_ids(self):
        bad = {"version": "1", "project": {"name": "x"},
               "nodes": [{"id": "a", "name": "A"}, {"id": "a", "name": "A2"}],
               "edges": []}
        errors, _ = render.validate_graph(bad)
        self.assertTrue(any("duplicate" in e for e in errors))

    def test_rejects_empty_nodes(self):
        bad = {"version": "1", "project": {"name": "x"}, "nodes": [], "edges": []}
        errors, _ = render.validate_graph(bad)
        self.assertTrue(errors)


class TestEnrichment(Base):
    def test_valid_enrichment_merges(self):
        enrich = {
            "project": {"description": "A fixture."},
            "nodes": {"file:src/main.py": {"summary": "Entry point.", "layer": "entry",
                                          "tags": ["boot"]}},
            "layers": {"entry": "Process entry points."},
            "tours": [{"title": "T", "steps": [{"nodeId": "file:src/main.py", "note": "start"}]}],
        }
        clean, warns = render.validate_enrich(enrich, self.ids)
        merged = render.merge(json.loads(json.dumps(self.graph)), clean)
        node = next(n for n in merged["nodes"] if n["id"] == "file:src/main.py")
        self.assertEqual(node["summary"], "Entry point.")
        self.assertEqual(node["tags"], ["boot"])
        self.assertEqual(merged["project"]["description"], "A fixture.")
        self.assertEqual(len(merged["tour"]), 1)
        self.assertEqual(merged["enrichedNodes"], 1)

    def test_unknown_node_ids_are_dropped_not_fatal(self):
        clean, warns = render.validate_enrich(
            {"nodes": {"file:does/not/exist.py": {"summary": "ghost"}}}, self.ids)
        self.assertEqual(clean["nodes"], {})
        self.assertTrue(any("unknown node ids" in w for w in warns))

    def test_tour_with_no_valid_steps_is_dropped(self):
        clean, warns = render.validate_enrich(
            {"tours": [{"title": "Ghost", "steps": [{"nodeId": "file:nope.py"}]}]}, self.ids)
        self.assertEqual(clean["tours"], [])
        self.assertTrue(any("Ghost" in w for w in warns))

    def test_string_shorthand_summary(self):
        clean, _ = render.validate_enrich(
            {"nodes": {"file:src/main.py": "just a string"}}, self.ids)
        self.assertEqual(clean["nodes"]["file:src/main.py"]["summary"], "just a string")

    def test_layer_override_applies(self):
        clean, _ = render.validate_enrich(
            {"nodes": {"file:src/utils/hashing.py": {"summary": "s", "layer": "data"}}}, self.ids)
        merged = render.merge(json.loads(json.dumps(self.graph)), clean)
        node = next(n for n in merged["nodes"] if n["id"] == "file:src/utils/hashing.py")
        self.assertEqual(node["layer"], "data")

    def test_garbage_enrichment_is_ignored(self):
        clean, warns = render.validate_enrich(["not", "a", "dict"], self.ids)
        self.assertEqual(clean, {})
        self.assertTrue(warns)


class TestOverview(Base):
    """The overview must summarize the real graph and never invent structure."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ov = overview.build(cls.graph)

    def test_builds_from_graph(self):
        self.assertIsNotNone(self.ov)
        self.assertTrue(self.ov["boxes"], "expected at least one module box")
        self.assertGreater(self.ov["width"], 0)
        self.assertGreater(self.ov["height"], 0)

    def test_boxes_are_real_modules(self):
        mod_ids = {n["id"] for n in self.graph["nodes"] if n["id"].startswith("mod:")}
        for b in self.ov["boxes"]:
            self.assertIn(b["id"], mod_ids, "overview invented module %r" % b["id"])

    def test_edges_reference_visible_boxes_only(self):
        ids = {b["id"] for b in self.ov["boxes"]}
        for e in self.ov["edges"]:
            self.assertIn(e["from"], ids)
            self.assertIn(e["to"], ids)
            self.assertNotEqual(e["from"], e["to"], "self-loop in overview")

    def test_every_edge_has_a_path(self):
        for e in self.ov["edges"]:
            self.assertTrue(e["d"].startswith("M"), "edge without geometry: %r" % e)

    def test_journey_hops_are_real_edges(self):
        pairs = {(e["from"], e["to"]) for e in self.ov["edges"]}
        for a, b in self.ov["journey"]:
            self.assertIn((a, b), pairs, "journey hop %s->%s is not an edge" % (a, b))

    def test_journey_is_contiguous(self):
        hops = self.ov["journey"]
        for i in range(len(hops) - 1):
            self.assertEqual(hops[i][1], hops[i + 1][0], "journey is not a single path")

    def test_boxes_do_not_overlap(self):
        """Geometry contract: no two boxes may intersect (glowmotion's C1 rule)."""
        bs = self.ov["boxes"]
        for i in range(len(bs)):
            for j in range(i + 1, len(bs)):
                a, b = bs[i], bs[j]
                overlap = (a["x"] < b["x"] + b["w"] and a["x"] + a["w"] > b["x"] and
                           a["y"] < b["y"] + b["h"] and a["y"] + a["h"] > b["y"])
                self.assertFalse(overlap, "%s overlaps %s" % (a["label"], b["label"]))

    def test_boxes_inside_canvas(self):
        for b in self.ov["boxes"]:
            self.assertGreaterEqual(b["x"], 0)
            self.assertGreaterEqual(b["y"], 0)
            self.assertLessEqual(b["x"] + b["w"], self.ov["width"])
            self.assertLessEqual(b["y"] + b["h"], self.ov["height"])

    def test_rows_cover_every_box(self):
        rows = {r["row"] for r in self.ov["rows"]}
        for b in self.ov["boxes"]:
            self.assertIn(b["row"], rows)

    def test_landscape_aspect(self):
        """A tall thin column is unreadable; the overview must stay wide-ish."""
        self.assertGreater(self.ov["width"] / self.ov["height"], 0.6)

    def test_deterministic(self):
        again = overview.build(self.graph)
        self.assertEqual(json.dumps(self.ov, sort_keys=True),
                         json.dumps(again, sort_keys=True))

    def test_config_only_module_is_omitted(self):
        """A directory of pure config (no source) is scaffolding, not architecture."""
        labels = {b["path"] for b in self.ov["boxes"]}
        # The fixture's repo root holds only package.json/requirements/README.
        self.assertNotIn(".", labels)

    def test_embedded_in_rendered_html(self):
        html = render.render_html(self.graph, "fixture")
        self.assertIn('"overview"', html)
        self.assertIn("buildOverview", html)

    def test_survives_graph_without_files(self):
        empty = {"version": "1", "project": {"name": "x"}, "nodes": [], "edges": []}
        self.assertIsNone(overview.build(empty))


class TestDocExtraction(Base):
    """A node with only numbers teaches nothing. The code already documents
    itself in ~90% of real repos, so read that instead of asking a model."""

    def test_extracts_python_module_docstring(self):
        q = chr(34) * 3
        doc = scan.extract_doc("python", q + "Thread-safe singleton state." + q + "\nimport os\n")
        self.assertEqual(doc, "Thread-safe singleton state.")

    def test_falls_back_to_first_definition(self):
        q = chr(34) * 3
        src = "import os\n\n\nclass Thing:\n    " + q + "Owns the widget lifecycle." + q + "\n"
        self.assertIn("widget lifecycle", scan.extract_doc("python", src))

    def test_stops_at_structured_sections(self):
        q = chr(34) * 3
        src = q + "Do the thing.\n\nArgs:\n    x: ignored\n" + q + "\n"
        doc = scan.extract_doc("python", src)
        self.assertEqual(doc, "Do the thing.")
        self.assertNotIn("ignored", doc)

    def test_skips_boilerplate_headers(self):
        for noise in ("#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n",
                      "// Copyright 2024 Someone\n// SPDX-License-Identifier: MIT\n"):
            lang = "python" if noise.startswith("#!") else "typescript"
            self.assertEqual(scan.extract_doc(lang, noise), "",
                             "boilerplate leaked into a summary: %r" % noise)

    def test_extracts_jsdoc_block(self):
        src = "/**\n * Streams query results over SSE.\n */\nexport function run() {}\n"
        self.assertIn("Streams query results", scan.extract_doc("typescript", src))

    def test_extracts_go_line_comments(self):
        src = "// Package store persists orders.\npackage store\n"
        self.assertIn("persists orders", scan.extract_doc("go", src))

    def test_summary_is_bounded(self):
        q = chr(34) * 3
        long = q + ("word " * 400) + q + "\n"
        self.assertLessEqual(len(scan.extract_doc("python", long)), 260)

    def test_docs_land_on_nodes(self):
        docs = [n for n in self.graph["nodes"] if n.get("doc")]
        self.assertTrue(docs, "no docstring reached any node")
        syms = [n for n in self.graph["nodes"] if n.get("symbols")]
        self.assertTrue(syms, "no symbol list reached any node")

    def test_docstring_fills_summary_but_agent_wins(self):
        graph = json.loads(json.dumps(self.graph))
        target = next(n for n in graph["nodes"] if n.get("doc"))
        merged = render.merge(graph, {})
        node = next(n for n in merged["nodes"] if n["id"] == target["id"])
        self.assertEqual(node["summary"], target["doc"])
        self.assertEqual(node["summarySource"], "docstring")
        # An agent summary must override the extracted one.
        graph2 = json.loads(json.dumps(self.graph))
        clean, _ = render.validate_enrich(
            {"nodes": {target["id"]: {"summary": "Agent knows better."}}},
            {n["id"] for n in graph2["nodes"]})
        merged2 = render.merge(graph2, clean)
        node2 = next(n for n in merged2["nodes"] if n["id"] == target["id"])
        self.assertEqual(node2["summary"], "Agent knows better.")
        self.assertEqual(node2["summarySource"], "agent")


class TestStarMap(Base):
    """The star map reads the same graph as mass instead of layers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sm = overview.build(cls.graph)["starmap"]

    def test_present_and_populated(self):
        self.assertTrue(self.sm["galaxies"])
        self.assertTrue(self.sm["stars"])

    def test_stars_inside_canvas(self):
        for s in self.sm["stars"]:
            self.assertGreaterEqual(s["x"], 0)
            self.assertGreaterEqual(s["y"], 0)
            self.assertLessEqual(s["x"], self.sm["width"])
            self.assertLessEqual(s["y"], self.sm["height"])

    def test_galaxies_do_not_collide(self):
        gs = self.sm["galaxies"]
        for i in range(len(gs)):
            for j in range(i + 1, len(gs)):
                a, b = gs[i], gs[j]
                d = ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5
                self.assertGreater(d, (a["r"] + b["r"]) * 0.55,
                                   "%s overlaps %s" % (a["label"], b["label"]))

    def test_magnitudes_are_spread_not_saturated(self):
        """A saturated field loses all ranking information."""
        mags = [s["mag"] for s in self.sm["stars"]]
        for m in mags:
            self.assertGreaterEqual(m, 0.0)
            self.assertLessEqual(m, 1.0)
        sat = sum(1 for m in mags if m >= 0.999)
        self.assertLess(sat, max(2, len(mags) * 0.25), "too many stars saturated")

    def test_links_reference_real_galaxies(self):
        ids = {g["id"] for g in self.sm["galaxies"]}
        for l in self.sm["links"]:
            self.assertIn(l["from"], ids)
            self.assertIn(l["to"], ids)

    def test_deterministic(self):
        again = overview.build(self.graph)["starmap"]
        self.assertEqual(json.dumps(self.sm, sort_keys=True),
                         json.dumps(again, sort_keys=True))

    def test_viewer_wires_the_view(self):
        tpl = render.load_template()
        for token in ('id="sky"', 'id="mStar"', "function drawSky", "paintStar",
                      "function skyHit", "starmap"):
            self.assertIn(token, tpl, "star map lost %r" % token)

    def test_stars_have_depth(self):
        """Without z there is nothing to rotate — the map would be a flat picture."""
        for s in self.sm["stars"]:
            self.assertIn("z", s)
        for g in self.sm["galaxies"]:
            self.assertIn("z", g)
        zs = [s["z"] for s in self.sm["stars"]]
        self.assertGreater(max(zs) - min(zs), 10, "disc has no thickness")

    def test_orbit_camera_wired(self):
        """Drag-to-rotate, wheel dolly, damping, pan and reset must all exist."""
        tpl = render.load_template()
        for token in ("function project", "function skyTick", "function skyReset",
                      "SKY.yaw", "SKY.pitch", "SKY.zoomTo", "SKY.vYaw",
                      "PITCH_MIN", "PITCH_MAX", "touchstart", "wheel"):
            self.assertIn(token, tpl, "orbit camera lost %r" % token)

    def test_projection_sorts_by_depth(self):
        """Painting order must be far-to-near or nearer stars get buried."""
        tpl = render.load_template()
        self.assertIn("b.depth - a.depth", tpl)

    def test_no_scale_field_shadowing(self):
        """project() returns `s` (scale); spreading a star as `s` shadowed its id
        and threw on every frame. Guard the fixed idiom."""
        tpl = render.load_template()
        self.assertNotIn("Object.assign({ s: s }, project", tpl)
        self.assertIn("p.star = st", tpl)


class TestViewerTemplate(Base):
    def test_viewer_file_exists_and_is_complete(self):
        self.assertTrue(os.path.isfile(render.VIEWER_PATH), "viewer.html is missing")
        tpl = render.load_template()
        self.assertIn("__DATA__", tpl)
        self.assertIn("__TITLE__", tpl)
        self.assertTrue(tpl.rstrip().endswith("</html>"))

    def test_animation_layer_present(self):
        """The motion layer is part of the contract; guard against regressions."""
        tpl = render.load_template()
        for token in ('id="fx"', "requestAnimationFrame(frame)", "buildPackets",
                      "drawPackets", "drawHalos", "drawStars", "setMotion",
                      "prefers-reduced-motion"):
            self.assertIn(token, tpl, "animation layer lost %r" % token)

    def test_motion_respects_reduced_preference(self):
        tpl = render.load_template()
        self.assertIn('matchMedia("(prefers-reduced-motion: reduce)")', tpl)
        self.assertIn("setMotion(!REDUCED)", tpl)

    def test_hierarchy_tree_is_complete(self):
        """Progressive disclosure needs a real tree: every ancestor must exist."""
        mods = {n["id"]: n for n in self.graph["nodes"] if n["type"] == "module"}
        self.assertTrue(mods)
        roots = [m for m in mods.values() if not m.get("parent")]
        self.assertEqual(len(roots), 1, "expected exactly one tree root")
        for m in mods.values():
            if m.get("parent"):
                self.assertIn(m["parent"], mods, "%s has a missing parent" % m["id"])

    def test_module_stats_roll_up(self):
        """A collapsed parent must report its whole subtree, or +N lies."""
        mods = {n["id"]: n for n in self.graph["nodes"] if n["type"] == "module"}
        root = next(m for m in mods.values() if not m.get("parent"))
        files = [n for n in self.graph["nodes"]
                 if n.get("type") in ("file", "config", "document")]
        self.assertEqual(root["fileCount"], len(files),
                         "root subtree count does not match the file total")
        for m in mods.values():
            kids = [c for c in mods.values() if c.get("parent") == m["id"]]
            if kids:
                self.assertGreaterEqual(
                    m["fileCount"], max(k["fileCount"] for k in kids),
                    "%s reports fewer files than a child" % m["id"])

    def test_containment_edges_link_modules(self):
        mods = {n["id"] for n in self.graph["nodes"] if n["type"] == "module"}
        pairs = {(e["source"], e["target"]) for e in self.graph["edges"]
                 if e["type"] == "contains"}
        for n in self.graph["nodes"]:
            if n["type"] == "module" and n.get("parent"):
                self.assertIn((n["parent"], n["id"]), pairs,
                              "no contains edge for %s" % n["id"])

    def test_hierarchy_viewer_wired(self):
        tpl = render.load_template()
        for token in ("function layoutTree", "function toggleExpand",
                      "function hiddenChildCount", "function openTo",
                      "S.open", "S.openFiles", 'id="bHier"', "MOD_KIDS",
                      "function openAtEntry", 'id="startHere"'):
            self.assertIn(token, tpl, "hierarchy lost %r" % token)

    def test_ask_context_wired(self):
        """Offline artifact: no API key, so it hands you a prompt instead."""
        tpl = render.load_template()
        self.assertIn("function copyAskContext", tpl)
        self.assertIn("data-ask", tpl)
        # Must ship real facts, not just a file name.
        for token in ("Depends on: ", "Used by: ", "Defines: ", "Question:"):
            self.assertIn(token, tpl, "ask prompt missing %r" % token)
        # And must never embed a key or call out to a model.
        self.assertNotRegex(tpl, r"""api[_-]?key\s*[:=]\s*["'][A-Za-z0-9]""")

    def test_declutter_controls_present(self):
        """Dense graphs are unreadable by default, so the simplifiers must exist."""
        tpl = render.load_template()
        for token in ("foldHubs", "neighborhood", "isFoldedHub", "HUB_MIN",
                      "HOOD_MAX", "computeDegrees", 'id="bFold"', 'id="bHood"'):
            self.assertIn(token, tpl, "declutter control lost %r" % token)

    def test_starts_simplified(self):
        """Defaults must favour readability: tests hidden, hubs folded, calls off."""
        tpl = render.load_template()
        self.assertIn('hiddenLayers: new Set(["test"])', tpl)
        self.assertRegex(tpl, r"foldHubs:\s*true")
        self.assertRegex(tpl, r"calls:\s*false")

    def test_folded_edges_are_recoverable(self):
        """Nothing may vanish silently — a hub advertises and reveals its edges."""
        tpl = render.load_template()
        self.assertIn("S.expanded.add(n.id)", tpl)   # click to expand
        self.assertIn('"⋯"', tpl)                    # badge showing the count

    def test_floating_panels_stack_above_views(self):
        """Regression: #ov (z-index 1) once covered the tour panel, eating its
        Prev/Next/Close clicks. Every floating panel must outrank the views."""
        tpl = render.load_template()
        flat = tpl.replace(" ", "").replace("\n", "")

        def z_of(pattern):
            m = re.search(pattern + r"[^}]*?z-index:(\d+)", flat)
            return int(m.group(1)) if m else None

        panel_z = z_of(r"\.panel\{")
        view_z = z_of(r"#ov\{")
        tour_z = z_of(r"#tour\{")
        self.assertIsNotNone(panel_z, ".panel has no explicit z-index")
        self.assertIsNotNone(view_z, "#ov has no explicit z-index")
        self.assertIsNotNone(tour_z, "#tour has no explicit z-index")
        self.assertGreater(panel_z, view_z, "panels would sit under the overview")
        self.assertGreaterEqual(tour_z, panel_z, "tour would sit under other panels")

    def test_tour_forces_explore_mode(self):
        """Tour steps address graph nodes, so it must not run over the overview."""
        tpl = render.load_template()
        self.assertRegex(tpl, r'if \(S\.mode !== "explore"\) setMode\("explore"\)')
        # Leaving explore must close the tour rather than orphan the panel.
        self.assertIn("if (S.tourIdx >= 0) closeTour();", tpl)
        # A modal alert would block the page; the button must self-disable instead.
        self.assertNotRegex(tpl, r"^\s*alert\(", "blocking alert() in the viewer")
        self.assertIn('tb.disabled = true', tpl)

    def test_select_follows_dark_theme(self):
        """Native dropdown popups are OS-painted; color-scheme is what themes them."""
        tpl = render.load_template()
        flat = tpl.replace(" ", "").replace("\n", "")
        self.assertIn("color-scheme:dark", flat)
        self.assertIn('html[data-theme="light"]select{color-scheme:light}', flat)
        self.assertIn("selectoption{", flat, "option colors missing for Windows/Linux")

    def test_edge_labels_and_flow_present(self):
        """Explore edges must be named and must visibly flow."""
        tpl = render.load_template()
        for token in ("drawEdgeLabels", "drawLiveEdges", "lineDashOffset",
                      "liveEdgesFor", "LIVE_EDGE_CAP"):
            self.assertIn(token, tpl, "edge animation lost %r" % token)
        # Every relationship the scanner emits needs a human-readable name.
        for label in ("imports", "calls", "depends on", "inherits", "contains"):
            self.assertIn('"%s"' % label, tpl, "no label for edge kind %r" % label)

    def test_live_edges_are_capped(self):
        """A high-degree hub must not blow the frame budget (was 1341 edges/36ms)."""
        tpl = render.load_template()
        self.assertRegex(tpl, r"LIVE_EDGE_CAP\s*=\s*\d+")
        cap = int(re.search(r"LIVE_EDGE_CAP\s*=\s*(\d+)", tpl).group(1))
        self.assertLessEqual(cap, 200, "cap too high to hold 60fps")
        self.assertGreaterEqual(cap, 40, "cap so low the effect disappears")

    def test_two_views_wired(self):
        """The merged contract: an overview view, an explore view, and the handoff."""
        tpl = render.load_template()
        for token in ('id="ov"', 'id="mOverview"', 'id="mExplore"',
                      "function setMode", "function drillInto", "function buildOverview",
                      "ov-box", "ov-link", "ov-comet", "animateMotion"):
            self.assertIn(token, tpl, "merged view lost %r" % token)

    def test_static_and_motion_use_separate_canvases(self):
        """Perf contract: the cached scene must not be repainted every frame."""
        tpl = render.load_template()
        self.assertIn('<canvas id="cv">', tpl)
        self.assertIn('<canvas id="fx">', tpl)
        self.assertIn("#fx{pointer-events:none}", tpl.replace(" ", "").replace("\n", ""))


class TestRendering(Base):
    def test_produces_self_contained_html(self):
        html = render.render_html(self.graph, "fixture")
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertNotIn("__DATA__", html)
        self.assertNotIn("__TITLE__", html)
        # No external resource loads: fully offline artifact.
        for bad in ('src="http', 'href="http', "cdn.", "unpkg", "googleapis"):
            self.assertNotIn(bad, html)

    def test_embedded_json_is_parseable_and_escaped(self):
        html = render.render_html(self.graph, "fixture")
        start = html.index('<script id="data" type="application/json">') + \
            len('<script id="data" type="application/json">')
        end = html.index("</script>", start)
        payload = html[start:end]
        # The payload must not contain a raw closing tag that would break the script.
        self.assertNotIn("</script", payload)
        data = json.loads(payload.replace("<\\/", "</"))
        self.assertEqual(len(data["nodes"]), len(self.graph["nodes"]))

    def test_slim_drops_internal_fields(self):
        slimmed = render.slim(self.graph)
        allowed_node_keys = {
            "id", "type", "name", "filePath", "module", "language", "layer", "loc",
            "fanIn", "fanOut", "importance", "isEntry", "defCount", "routes",
            "httpVerbs", "title", "summary", "tags", "lineRange", "kind",
            "fileCount", "languages", "usedBy", "importCount",
            "doc", "symbols", "summarySource", "parent", "depth", "ownFiles",
        }
        for n in slimmed["nodes"]:
            self.assertTrue(set(n).issubset(allowed_node_keys),
                            "unexpected keys survived slim(): %s" % (set(n) - allowed_node_keys))
        for e in slimmed["edges"]:
            self.assertTrue(set(e).issubset({"source", "target", "type", "line"}))
        # Empty values are stripped to keep the embedded payload small.
        for n in slimmed["nodes"]:
            self.assertNotIn("", n.values())

    def test_atomic_delivery_writes_file(self):
        out = os.path.join(self.tmp, "out", "codegraph.html")
        render.deliver(render.render_html(self.graph, "t"), out)
        self.assertTrue(os.path.isfile(out))
        self.assertGreater(os.path.getsize(out), 5000)

    def test_failed_render_leaves_no_partial_file(self):
        out = os.path.join(self.tmp, "fail", "codegraph.html")
        with self.assertRaises(ValueError):
            render.deliver("no placeholders replaced __DATA__", out)
        self.assertFalse(os.path.exists(out))
        leftovers = [f for f in os.listdir(os.path.dirname(out))
                     if f.startswith(".codegraph-")]
        self.assertEqual(leftovers, [])


class TestCLI(Base):
    def test_end_to_end_cli(self):
        out_dir = os.path.join(self.tmp, "cli", ".codegraph")
        r1 = subprocess.run(
            [sys.executable, os.path.join(HERE, "scan.py"), self.repo, "-o", out_dir],
            capture_output=True, text=True)
        self.assertEqual(r1.returncode, 0, r1.stderr)
        self.assertTrue(os.path.isfile(os.path.join(out_dir, "graph.json")))
        self.assertTrue(os.path.isfile(os.path.join(out_dir, "digest.md")))

        r2 = subprocess.run(
            [sys.executable, os.path.join(HERE, "render.py"), "--in", out_dir],
            capture_output=True, text=True)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertTrue(os.path.isfile(os.path.join(out_dir, "codegraph.html")))

    def test_validate_only_writes_nothing(self):
        out_dir = os.path.join(self.tmp, "vo", ".codegraph")
        subprocess.run([sys.executable, os.path.join(HERE, "scan.py"), self.repo,
                        "-o", out_dir, "--quiet"], check=True)
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "render.py"), "--in", out_dir,
             "--validate-only"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(out_dir, "codegraph.html")))

    def test_render_fails_without_graph(self):
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "render.py"), "--in",
             os.path.join(self.tmp, "nonexistent")], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("scan.py first", r.stderr)

    def test_scan_rejects_bad_path(self):
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "scan.py"),
             os.path.join(self.tmp, "nope")], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)


class TestEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="codegraph-edge-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_empty_repo_exits_cleanly(self):
        empty = os.path.join(self.tmp, "empty")
        os.makedirs(empty)
        r = subprocess.run([sys.executable, os.path.join(HERE, "scan.py"), empty],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no source files", r.stderr)

    def test_single_file_repo(self):
        one = os.path.join(self.tmp, "one")
        os.makedirs(one)
        with open(os.path.join(one, "a.py"), "w") as fh:
            fh.write("def f():\n    return 1\n")
        scanned = scan.scan(one, 4000, True, 250)
        graph = scan.build_graph(scanned)
        errors, _ = render.validate_graph(graph)
        self.assertEqual(errors, [])
        html = render.render_html(graph, "one")
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn("file:a.py", html)

    def test_unicode_and_quotes_survive_render(self):
        u = os.path.join(self.tmp, "uni")
        os.makedirs(u)
        with open(os.path.join(u, "emoji.py"), "w", encoding="utf-8") as fh:
            fh.write('"""Docs with "quotes" and 中文 and \\ backslash."""\n\ndef f():\n    return 1\n')
        graph = scan.build_graph(scan.scan(u, 4000, True, 250))
        clean, _ = render.validate_enrich(
            {"nodes": {"file:emoji.py": {"summary": 'Has "quotes", 中文, </script> and \\ chars'}}},
            {n["id"] for n in graph["nodes"]})
        merged = render.merge(graph, clean)
        html = render.render_html(merged, "uni")
        self.assertNotIn("</script>", html[html.index('id="data"'):html.index("</script>",
                                                                             html.index('id="data"'))])
        self.assertIn("中文", html)

    def test_file_without_trailing_newline(self):
        p = os.path.join(self.tmp, "nonl")
        os.makedirs(p)
        with open(os.path.join(p, "x.py"), "w") as fh:
            fh.write("def f(): pass")
        graph = scan.build_graph(scan.scan(p, 4000, True, 250))
        self.assertTrue(any(n["id"] == "file:x.py" for n in graph["nodes"]))

    def test_max_files_truncation_is_reported(self):
        many = os.path.join(self.tmp, "many")
        os.makedirs(many)
        for i in range(12):
            with open(os.path.join(many, "m%d.py" % i), "w") as fh:
                fh.write("x = %d\n" % i)
        scanned = scan.scan(many, max_files=5, want_calls=False, symbols_for=10)
        self.assertTrue(scanned["stats"]["truncated"])
        self.assertLessEqual(scanned["stats"]["files_indexed"], 5)


if __name__ == "__main__":
    unittest.main(verbosity=2 if "-v" in sys.argv else 1)

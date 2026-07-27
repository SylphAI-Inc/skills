#!/usr/bin/env python3
"""
codegraph scan — deterministic codebase -> structural graph extraction.

Stage 1 of 3 in the codegraph pipeline:

    scan.py  ->  graph.json + digest.md        (this file, deterministic)
    agent    ->  enrich.json                   (semantic layer: summaries, layers, tours)
    render.py -> codegraph.html                (single self-contained interactive artifact)

Design contract:
  * ZERO third-party dependencies (stdlib only, Python 3.8+).
  * Same input -> same output. No LLM calls, no network, no randomness.
  * Never reads a file twice; caps work on pathological repos.
  * Emits a compact digest.md so an agent can understand the whole repo
    WITHOUT loading the (potentially huge) graph.json into its context.

Usage:
    python3 scan.py [ROOT] [-o OUTDIR] [--max-files N] [--no-calls] [--symbols-for N]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict

SCHEMA_VERSION = "1.0.0"

BACKSLASH = chr(92)
QUOTE_CHARS = '"' + "'"
QUOTE_OR_TICK = QUOTE_CHARS + "`"

# --------------------------------------------------------------------------------------
# Language table
# --------------------------------------------------------------------------------------

LANG_BY_EXT = {
    ".py": "python", ".pyi": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript", ".cts": "typescript",
    ".vue": "vue", ".svelte": "svelte",
    ".go": "go",
    ".rs": "rust",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin", ".scala": "scala",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".c": "c", ".h": "c",
    ".cc": "cpp", ".cpp": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp",
    ".swift": "swift",
    ".m": "objc", ".mm": "objc",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell",
    ".sql": "sql",
    ".tf": "terraform",
    ".proto": "proto",
    ".graphql": "graphql", ".gql": "graphql",
}

# Non-code files worth keeping as graph nodes (config / docs / infra).
SUPPORT_FILES = {
    ".json": "config", ".yaml": "config", ".yml": "config", ".toml": "config",
    ".ini": "config", ".cfg": "config", ".env": "config",
    ".md": "document", ".mdx": "document", ".rst": "document", ".txt": "document",
}

DOCKER_NAMES = {"dockerfile", "docker-compose.yml", "docker-compose.yaml", "makefile"}

# Directories never worth walking.
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".tox", ".nox", "venv", ".venv", "env", ".env.d", "site-packages",
    "dist", "build", "out", "target", ".next", ".nuxt", ".svelte-kit", ".turbo",
    "coverage", "htmlcov", ".coverage", ".idea", ".vscode", ".gradle", ".cache",
    "vendor", "bower_components", "Pods", ".terraform", ".serverless", ".parcel-cache",
    "codegraph_out", ".codegraph",
}

SKIP_FILE_RE = re.compile(
    r"(\.min\.(js|css)$|\.bundle\.js$|-lock\.(json|yaml)$|\.lock$|\.map$|"
    r"\.snap$|\.pb\.go$|_pb2\.py$|\.generated\.|\.g\.dart$)",
    re.IGNORECASE,
)

MAX_FILE_BYTES = 900_000       # skip anything bigger; almost certainly generated
MAX_LINE_LEN_AVG = 400         # skip minified-looking files


# --------------------------------------------------------------------------------------
# Layer heuristics (the agent may override these in enrich.json)
# --------------------------------------------------------------------------------------

LAYER_RULES = [
    ("test",     r"(^|/)(tests?|specs?|__tests__|e2e|fixtures?)(/|$)|(_test|\.test|\.spec|_spec)\."),
    ("entry",    r"(^|/)(main|index|app|server|cli|__main__|manage|bootstrap|wsgi|asgi)\.[a-z]+$|(^|/)(cmd|bin|scripts?)(/|$)"),
    ("config",   r"(^|/)(config|configs|settings|conf)(/|$)|(^|/)\.?[a-z]*(rc|config)\.[a-z]+$"),
    ("infra",    r"(^|/)(deploy|infra|terraform|k8s|kubernetes|helm|\.github|docker)(/|$)|dockerfile|docker-compose"),
    ("ui",       r"(^|/)(ui|views?|components?|pages?|screens?|templates?|widgets?|styles?|layouts?|themes?)(/|$)"
                 r"|\.(vue|svelte|tsx|jsx|css|scss)$|(component|view|page|screen|widget|modal|button)s?\.[a-z]+$"),
    ("api",      r"(^|/)(api|routes?|routers?|controllers?|handlers?|endpoints?|graphql|resolvers?|middleware|rpc|grpc|rest|web|http|server|net|protocols?|transport)(/|$)"
                 r"|(route|router|controller|handler|endpoint|resolver|middleware|client|server|request|response|session|connection|socket|url)s?\.[a-z]+$"),
    ("data",     r"(^|/)(models?|entities|schemas?|db|database|migrations?|repositor(y|ies)|dao|store|stores|persistence|dialects?|orm|sql|query|queries|records?|serializers?|codecs?)(/|$)"
                 r"|(model|entity|schema|table|column|row|record|query|cursor|dialect|serializer|migration|type|types|field)s?\.[a-z]+$"),
    ("service",  r"(^|/)(services?|domain|core|usecases?|business|logic|managers?|workers?|jobs?|tasks?|agents?|engines?|processors?|pipelines?|events?|commands?)(/|$)"
                 r"|(service|manager|worker|engine|processor|pipeline|scheduler|dispatcher|executor|runner|event|command|hook)s?\.[a-z]+$"),
    ("util",     r"(^|/)(utils?|helpers?|lib|libs|common|shared|internal|support|tools?|ext|extensions?|compat|vendor|_compat)(/|$)"
                 r"|(util|utils|helper|compat|constant|exception|error|log|logger|logging|typing|base|mixin|decorator|context|registry|cache|pool|inspect|inspection|visitor|traversal|annotation|deprecation)s?\.[a-z]+$"),
    ("docs",     r"(^|/)(docs?|documentation|examples?|samples?)(/|$)|\.(md|mdx|rst)$"),
]

LAYER_ORDER = ["entry", "ui", "api", "service", "data", "util", "config", "infra", "test", "docs", "other"]

LAYER_LABELS = {
    "entry": "Entry Points", "ui": "UI / Presentation", "api": "API / Interface",
    "service": "Business Logic", "data": "Data / Persistence", "util": "Utilities",
    "config": "Configuration", "infra": "Infrastructure", "test": "Tests",
    "docs": "Documentation", "other": "Other",
}


def guess_layer(rel_path: str) -> str:
    low = rel_path.lower()
    for layer, pattern in LAYER_RULES:
        if re.search(pattern, low):
            return layer
    return "other"


# --------------------------------------------------------------------------------------
# Regex extractors, per language family
# --------------------------------------------------------------------------------------

RE = {
    "py_import": re.compile(r"^\s*(?:from\s+([.\w]+)\s+import\s+([^\n#]+)|import\s+([^\n#]+))", re.M),
    "py_def": re.compile(r"^(?P<indent>[ \t]*)(?:async\s+)?def\s+(?P<name>\w+)\s*\(", re.M),
    "py_class": re.compile(r"^(?P<indent>[ \t]*)class\s+(?P<name>\w+)\s*[\(:]", re.M),

    "js_import": re.compile(
        r"""(?:^|\s)import\s+(?:[\w*{}\s,$]+\s+from\s+)?['"]([^'"]+)['"]"""
        r"""|require\(\s*['"]([^'"]+)['"]\s*\)"""
        r"""|(?:^|\s)export\s+(?:\*|\{[^}]*\})\s+from\s+['"]([^'"]+)['"]"""
        r"""|import\(\s*['"]([^'"]+)['"]\s*\)""",
        re.M,
    ),
    "js_func": re.compile(
        r"^(?P<indent>[ \t]*)(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*(?P<name>\w+)",
        re.M,
    ),
    "js_arrow": re.compile(
        r"^(?P<indent>[ \t]*)(?:export\s+)?(?:default\s+)?(?:const|let|var)\s+(?P<name>\w+)\s*"
        r"(?::[^=\n]+)?=\s*(?:async\s*)?(?:\([^)]*\)|\w+)\s*=>",
        re.M,
    ),
    "js_class": re.compile(
        r"^(?P<indent>[ \t]*)(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(?P<name>\w+)"
        r"(?:\s+extends\s+(?P<base>[\w.]+))?",
        re.M,
    ),
    "js_type": re.compile(
        r"^(?P<indent>[ \t]*)(?:export\s+)?(?:interface|type|enum)\s+(?P<name>\w+)", re.M),
    "js_export": re.compile(r"^\s*export\s+(?:default\s+)?(?:const|let|var|function|class|interface|type|enum)?\s*(\w+)?", re.M),

    "go_import_block": re.compile(r"import\s*\(([^)]*)\)", re.S),
    "go_import_one": re.compile(r'^\s*import\s+(?:[\w.]+\s+)?"([^"]+)"', re.M),
    "go_import_line": re.compile(r'^\s*(?:[\w.]+\s+)?"([^"]+)"', re.M),
    "go_func": re.compile(r"^func\s+(?:\((?P<recv>[^)]*)\)\s*)?(?P<name>\w+)\s*[\(\[]", re.M),
    "go_type": re.compile(r"^type\s+(?P<name>\w+)\s+(?P<kind>struct|interface|func|\w+)", re.M),

    "rs_use": re.compile(r"^\s*(?:pub\s+)?use\s+([^;]+);", re.M),
    "rs_mod": re.compile(r"^\s*(?:pub\s+)?mod\s+(\w+)\s*;", re.M),
    "rs_fn": re.compile(r"^(?P<indent>[ \t]*)(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+(?P<name>\w+)", re.M),
    "rs_type": re.compile(r"^(?P<indent>[ \t]*)(?:pub(?:\([^)]*\))?\s+)?(?:struct|enum|trait|union)\s+(?P<name>\w+)", re.M),
    "rs_impl": re.compile(r"^(?P<indent>[ \t]*)impl(?:<[^>]*>)?\s+(?:(?P<trait>[\w:<>]+)\s+for\s+)?(?P<name>[\w:<>]+)", re.M),

    "jvm_import": re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)(?:\.\*)?\s*;?", re.M),
    "jvm_pkg": re.compile(r"^\s*package\s+([\w.]+)", re.M),
    "jvm_type": re.compile(
        r"^(?P<indent>[ \t]*)(?:public\s+|private\s+|protected\s+|internal\s+|abstract\s+|final\s+|sealed\s+|open\s+|data\s+|static\s+)*"
        r"(?:class|interface|enum|object|record|trait)\s+(?P<name>\w+)"
        r"(?:[^\n{]*?(?:extends|:)\s+(?P<base>[\w.<>]+))?",
        re.M,
    ),
    "jvm_method": re.compile(
        r"^(?P<indent>[ \t]{2,})(?:public\s+|private\s+|protected\s+|internal\s+|static\s+|final\s+|override\s+|suspend\s+|async\s+)*"
        r"(?:fun\s+(?P<kname>\w+)|(?:[\w<>\[\],?.]+)\s+(?P<jname>\w+)\s*\()",
        re.M,
    ),

    "rb_require": re.compile(r"""^\s*require(?:_relative)?\s+['"]([^'"]+)['"]""", re.M),
    "rb_def": re.compile(r"^(?P<indent>[ \t]*)def\s+(?P<name>[\w.?!=]+)", re.M),
    "rb_class": re.compile(r"^(?P<indent>[ \t]*)(?:class|module)\s+(?P<name>[\w:]+)(?:\s*<\s*(?P<base>[\w:]+))?", re.M),

    "php_use": re.compile(
        r"""^\s*(?:use|require(?:_once)?|include(?:_once)?)\s+['"(]?([^'"\s;()]+)""", re.M),
    "php_def": re.compile(r"^(?P<indent>[ \t]*)(?:(?:public|private|protected|static|abstract|final)\s+)*"
                          r"(?:function\s+(?P<name>\w+)|(?:class|interface|trait)\s+(?P<cname>\w+))", re.M),

    "cs_using": re.compile(r"^\s*using\s+(?:static\s+)?([\w.]+)\s*;", re.M),
    "c_include": re.compile(r'^\s*#\s*include\s+[<"]([^>"]+)[>"]', re.M),
    "c_func": re.compile(r"^(?:[\w*&:<>\[\]]+\s+){1,4}(?P<name>\w+)\s*\([^;]*\)\s*\{", re.M),
    "c_type": re.compile(r"^(?:typedef\s+)?(?:struct|class|enum|union|namespace)\s+(?P<name>\w+)", re.M),

    "swift_import": re.compile(r"^\s*import\s+(\w+)", re.M),
    "swift_def": re.compile(r"^(?P<indent>[ \t]*)(?:public\s+|private\s+|internal\s+|open\s+|final\s+|static\s+)*"
                            r"(?:func\s+(?P<name>\w+)|(?:class|struct|enum|protocol|extension)\s+(?P<cname>\w+))", re.M),

    "sh_source": re.compile(r"^\s*(?:source|\.)\s+([\w./$-]+)", re.M),
    "sh_func": re.compile(r"^(?:function\s+)?(?P<name>[\w-]+)\s*\(\)\s*\{", re.M),

    "tf_resource": re.compile(r'^(resource|module|data)\s+"([^"]+)"(?:\s+"([^"]+)")?', re.M),
    "sql_def": re.compile(r"CREATE\s+(?:OR\s+REPLACE\s+)?(TABLE|VIEW|INDEX|FUNCTION|PROCEDURE)\s+"
                          r"""(?:IF\s+NOT\s+EXISTS\s+)?[`"\[]?([\w.]+)""", re.I),
    "gql_def": re.compile(r"^\s*(type|input|enum|interface|union|scalar)\s+(\w+)", re.M),
    "proto_def": re.compile(r"^\s*(message|service|enum)\s+(\w+)", re.M),

    "vue_script": re.compile(r"<script[^>]*>(.*?)</script>", re.S),
    # Only trust route strings that appear in a real route-declaration context,
    # otherwise docstrings and example URLs create phantom entry points.
    "route_str": re.compile(
        r"""(?:@(?:\w+\.)*(?:route|get|post|put|patch|delete|api_route)|"""
        r"""\.(?:route|get|post|put|patch|delete|use|all)|"""
        r"""(?:^|\s)(?:path|url|re_path|Route|HandleFunc|register|add_url_rule))"""
        r"""\s*\(\s*[^)"']*["'](/[\w:{}\-./]*)["']""",
        re.M,
    ),
    "http_verb": re.compile(r"\.(get|post|put|patch|delete|head|options)\s*\(", re.I),
}

# Identifiers too generic to trust for cross-file call inference.
CALL_STOPWORDS = {
    "main", "run", "get", "set", "init", "test", "log", "print", "error", "data", "value",
    "name", "type", "id", "self", "this", "new", "add", "list", "map", "filter", "reduce",
    "start", "stop", "close", "open", "read", "write", "send", "load", "save", "next",
    "then", "catch", "push", "pop", "call", "apply", "bind", "keys", "items", "length",
    "string", "number", "object", "array", "boolean", "true", "false", "none", "null",
    "config", "options", "params", "args", "kwargs", "result", "response", "request",
    "create", "update", "delete", "remove", "find", "parse", "format", "build", "make",
    "handle", "process", "execute", "validate", "check", "render", "setup", "clone",
}

IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{3,}\b")
COMMENT_STRIP = {
    "hash": re.compile(r"#.*$", re.M),
    "slash": re.compile(r"//.*$|/\*.*?\*/", re.M | re.S),
}


# --------------------------------------------------------------------------------------
# File discovery
# --------------------------------------------------------------------------------------

def git_tracked_files(root: str):
    """Use git for discovery when available: respects .gitignore exactly, and is fast."""
    try:
        out = subprocess.run(
            ["git", "-C", root, "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True, text=True, timeout=45,
        )
        if out.returncode != 0:
            return None
        files = [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
        return files or None
    except (OSError, subprocess.SubprocessError):
        return None


def walk_files(root: str):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
                       or d in (".github",)]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            found.append(os.path.relpath(full, root))
    return found


def classify(rel_path: str):
    """Return (kind, language) or (None, None) if the file should be ignored."""
    base = os.path.basename(rel_path).lower()
    ext = os.path.splitext(base)[1]
    if SKIP_FILE_RE.search(base):
        return None, None
    if any(part in SKIP_DIRS for part in rel_path.split(os.sep)[:-1]):
        return None, None
    if ext in LANG_BY_EXT:
        return "code", LANG_BY_EXT[ext]
    if base in DOCKER_NAMES or base.startswith("dockerfile"):
        return "infra", "docker"
    if ext in SUPPORT_FILES:
        return SUPPORT_FILES[ext], "text"
    return None, None


def read_text(path: str):
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


# --------------------------------------------------------------------------------------
# Symbol / import extraction
# --------------------------------------------------------------------------------------

def _block_end_by_indent(lines, start_idx: int, indent: str) -> int:
    """End line (1-based) of an indentation-delimited block (Python/Ruby-ish)."""
    base = len(indent.expandtabs(4))
    last = start_idx
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        if not line.strip():
            continue
        cur = len(line[: len(line) - len(line.lstrip())].expandtabs(4))
        if cur <= base:
            break
        last = i
    return last + 1


def _block_end_by_brace(text: str, start_pos: int, max_lines: int = 4000) -> int:
    """End line (1-based) of a brace-delimited block starting at/after start_pos."""
    depth = 0
    seen = False
    i = start_pos
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "{":
            depth += 1
            seen = True
        elif ch == "}":
            depth -= 1
            if seen and depth <= 0:
                return text.count("\n", 0, i) + 1
        elif ch in QUOTE_OR_TICK:
            quote = ch
            i += 1
            while i < n and text[i] != quote:
                if text[i] == BACKSLASH:
                    i += 1
                i += 1
        i += 1
    return min(text.count("\n", 0, start_pos) + 1 + max_lines, text.count("\n") + 1)


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


# --------------------------------------------------------------------------------------
# Self-documentation: most codebases already describe themselves in docstrings and
# file-header comments. Reading them costs nothing and is the difference between a
# node that says "1674 LOC" and one that says what the file is FOR.
# --------------------------------------------------------------------------------------

_PY_DOC = re.compile(r'^\s*(?:[rubRUB]{0,2})("""|\'\'\')(.*?)\1', re.S)
_BLOCK_DOC = re.compile(r'^\s*/\*\*?(.*?)\*/', re.S)
_LINE_DOC = re.compile(r'^((?:\s*(?://|#|--)[^\n]*\n)+)')
_NOISE = re.compile(r'^(#!|-\*-|coding[:=]|type:\s*ignore|eslint|prettier|@ts-|flake8|noqa|'
                    r'pylint|mypy|ruff|fmt:|Copyright|SPDX|Licensed|All rights)', re.I)


def _clean_doc(raw: str) -> str:
    """Collapse a docstring/comment block into one useful sentence."""
    lines = []
    for ln in raw.split("\n"):
        ln = ln.strip()
        ln = re.sub(r'^(?://+|#+|--+|\*+)\s?', "", ln).strip()
        if not ln or _NOISE.match(ln):
            continue
        # Stop at structured sections; the prose above them is the summary.
        if re.match(r'^(Args|Arguments|Returns|Raises|Yields|Example[s]?|Note[s]?|'
                    r'Usage|Attributes|Params?|TODO|FIXME)\s*:?\s*$', ln, re.I):
            break
        if re.match(r'^[-=~#*_]{3,}$', ln):        # rule lines
            continue
        lines.append(ln)
        if len(" ".join(lines)) > 400:
            break
    doc = " ".join(lines).strip()
    if not doc:
        return ""
    # Prefer the first 1-2 sentences: a node tooltip is not a manual.
    parts = re.split(r'(?<=[.!?。])\s+', doc)
    out = parts[0]
    if len(out) < 60 and len(parts) > 1:
        out += " " + parts[1]
    return out[:260].strip()


def extract_doc(language: str, text: str) -> str:
    """Best-effort 'what is this file' sentence, taken from the code itself."""
    head = text[:4000]
    if language == "python":
        m = _PY_DOC.match(head)
        if m:
            return _clean_doc(m.group(2))
        # No module docstring: fall back to the first class/def that has one.
        m = re.search(r'^\s*(?:async\s+)?(?:def|class)\s+\w+[^\n]*:\s*\n\s*("""|\'\'\')(.*?)\1',
                      head, re.S | re.M)
        if m:
            return _clean_doc(m.group(2))
        return ""
    if language in ("javascript", "typescript", "vue", "svelte", "go", "rust", "java",
                    "kotlin", "scala", "csharp", "c", "cpp", "objc", "swift", "php"):
        m = _BLOCK_DOC.match(head)
        if m:
            return _clean_doc(m.group(1))
        m = _LINE_DOC.match(head)
        if m:
            return _clean_doc(m.group(1))
        # Doc comment attached to the first declaration rather than the file top.
        m = re.search(r'(/\*\*(?:[^*]|\*(?!/))*\*/)\s*(?:export\s+)?'
                      r'(?:async\s+)?(?:function|class|const|interface|type|func|pub|struct)',
                      head)
        if m:
            return _clean_doc(m.group(1)[3:-2])
        return ""
    if language in ("shell", "ruby", "terraform"):
        m = _LINE_DOC.match(head)
        if m:
            return _clean_doc(m.group(1))
    return ""


def extract(language: str, text: str, rel_path: str):
    """Return dict(imports=[raw specifiers], defs=[{kind,name,line,end_line,base}], extras={})."""
    imports = []
    defs = []
    extras = {}
    lines = text.split("\n")

    def add_def(kind, name, pos, end_line=None, base=None, indent=""):
        if not name:
            return
        start = line_of(text, pos)
        if end_line is None:
            end_line = _block_end_by_brace(text, pos) if language not in ("python", "ruby") \
                else _block_end_by_indent(lines, start - 1, indent)
        defs.append({
            "kind": kind, "name": name, "line": start,
            "end_line": max(end_line, start), "base": base,
            "top": len(indent.expandtabs(4)) == 0,
        })

    if language == "vue" or language == "svelte":
        blocks = RE["vue_script"].findall(text)
        inner = "\n".join(blocks) if blocks else ""
        for m in RE["js_import"].finditer(inner or text):
            imports.append(next(g for g in m.groups() if g))
        language = "typescript" if 'lang="ts"' in text or "lang='ts'" in text else "javascript"
        text_for_defs = inner or text
        for key, kind in (("js_func", "function"), ("js_arrow", "function"),
                          ("js_class", "class"), ("js_type", "type")):
            for m in RE[key].finditer(text_for_defs):
                add_def(kind, m.group("name"), text.find(m.group(0)) if inner else m.start(),
                        indent=m.groupdict().get("indent", ""))
        return {"imports": imports, "defs": defs, "extras": extras}

    if language == "python":
        for m in RE["py_import"].finditer(text):
            frm, _names, plain = m.group(1), m.group(2), m.group(3)
            if frm:
                imports.append(frm)
            elif plain:
                for part in plain.split(","):
                    mod = part.strip().split(" as ")[0].strip()
                    if mod:
                        imports.append(mod)
        for key, kind in (("py_class", "class"), ("py_def", "function")):
            for m in RE[key].finditer(text):
                add_def(kind, m.group("name"), m.start(), indent=m.group("indent"))

    elif language in ("javascript", "typescript"):
        for m in RE["js_import"].finditer(text):
            spec = next((g for g in m.groups() if g), None)
            if spec:
                imports.append(spec)
        for key, kind in (("js_func", "function"), ("js_arrow", "function"),
                          ("js_class", "class"), ("js_type", "type")):
            for m in RE[key].finditer(text):
                add_def(kind, m.group("name"), m.start(),
                        base=m.groupdict().get("base"), indent=m.group("indent"))
        verbs = RE["http_verb"].findall(text)
        if verbs:
            extras["http_verbs"] = sorted(set(v.lower() for v in verbs))

    elif language == "go":
        blocks = RE["go_import_block"].findall(text)
        for blk in blocks:
            imports.extend(RE["go_import_line"].findall(blk))
        imports.extend(RE["go_import_one"].findall(text))
        for m in RE["go_func"].finditer(text):
            recv = (m.group("recv") or "").split()
            owner = recv[-1].lstrip("*") if recv else None
            add_def("method" if owner else "function", m.group("name"), m.start(), base=owner)
        for m in RE["go_type"].finditer(text):
            add_def("class" if m.group("kind") in ("struct", "interface") else "type",
                    m.group("name"), m.start())

    elif language == "rust":
        for m in RE["rs_use"].finditer(text):
            imports.append(m.group(1).strip().split(" as ")[0])
        for name in RE["rs_mod"].findall(text):
            imports.append("mod::" + name)
        for key, kind in (("rs_fn", "function"), ("rs_type", "class"), ("rs_impl", "impl")):
            for m in RE[key].finditer(text):
                add_def(kind, m.group("name"), m.start(),
                        base=m.groupdict().get("trait"), indent=m.group("indent"))

    elif language in ("java", "kotlin", "scala"):
        imports.extend(RE["jvm_import"].findall(text))
        pkg = RE["jvm_pkg"].search(text)
        if pkg:
            extras["package"] = pkg.group(1)
        for m in RE["jvm_type"].finditer(text):
            add_def("class", m.group("name"), m.start(),
                    base=m.groupdict().get("base"), indent=m.group("indent"))
        for m in RE["jvm_method"].finditer(text):
            add_def("method", m.group("kname") or m.group("jname"), m.start(),
                    indent=m.group("indent"))

    elif language == "ruby":
        imports.extend(RE["rb_require"].findall(text))
        for key, kind in (("rb_class", "class"), ("rb_def", "function")):
            for m in RE[key].finditer(text):
                add_def(kind, m.group("name"), m.start(),
                        base=m.groupdict().get("base"), indent=m.group("indent"))

    elif language == "php":
        imports.extend(RE["php_use"].findall(text))
        for m in RE["php_def"].finditer(text):
            add_def("class" if m.group("cname") else "function",
                    m.group("cname") or m.group("name"), m.start(), indent=m.group("indent"))

    elif language == "csharp":
        imports.extend(RE["cs_using"].findall(text))
        for m in RE["jvm_type"].finditer(text):
            add_def("class", m.group("name"), m.start(),
                    base=m.groupdict().get("base"), indent=m.group("indent"))
        for m in RE["jvm_method"].finditer(text):
            add_def("method", m.group("kname") or m.group("jname"), m.start(),
                    indent=m.group("indent"))

    elif language in ("c", "cpp", "objc"):
        imports.extend(RE["c_include"].findall(text))
        for m in RE["c_type"].finditer(text):
            add_def("class", m.group("name"), m.start())
        for m in RE["c_func"].finditer(text):
            add_def("function", m.group("name"), m.start())

    elif language == "swift":
        imports.extend(RE["swift_import"].findall(text))
        for m in RE["swift_def"].finditer(text):
            add_def("class" if m.group("cname") else "function",
                    m.group("cname") or m.group("name"), m.start(), indent=m.group("indent"))

    elif language == "shell":
        imports.extend(RE["sh_source"].findall(text))
        for m in RE["sh_func"].finditer(text):
            add_def("function", m.group("name"), m.start())

    elif language == "terraform":
        for kind, a, b in RE["tf_resource"].findall(text):
            add_def("resource", (b or a), text.find(a))

    elif language == "sql":
        for kind, name in RE["sql_def"].findall(text):
            add_def("table" if kind.upper() in ("TABLE", "VIEW") else "function", name,
                    text.lower().find(name.lower()))

    elif language == "graphql":
        for kind, name in RE["gql_def"].findall(text):
            add_def("schema", name, text.find(name))

    elif language == "proto":
        for kind, name in RE["proto_def"].findall(text):
            add_def("service" if kind == "service" else "schema", name, text.find(name))

    # Route strings are a strong signal of "this file is an entry surface".
    if language in ("python", "javascript", "typescript", "go", "ruby", "php", "java", "kotlin"):
        routes = [r for r in RE["route_str"].findall(text)
                  if 1 < len(r) < 60 and "//" not in r][:12]
        if routes:
            extras["routes"] = sorted(set(routes))

    return {"imports": imports, "defs": defs, "extras": extras}


# --------------------------------------------------------------------------------------
# Import resolution
# --------------------------------------------------------------------------------------

JS_EXTS = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte", ".mts", ".cts"]
SRC_ROOTS = ["", "src", "lib", "app", "source", "packages", "internal", "pkg", "server", "client"]


class Resolver:
    def __init__(self, root: str, files):
        self.root = root
        self.files = set(files)
        self.by_basename = defaultdict(list)
        self.by_stem = defaultdict(list)
        for f in files:
            base = os.path.basename(f)
            self.by_basename[base].append(f)
            self.by_stem[os.path.splitext(base)[0]].append(f)
        self.go_module = self._go_module()
        self.dirs = {os.path.dirname(f) for f in files}

    def _go_module(self):
        gomod = os.path.join(self.root, "go.mod")
        if os.path.exists(gomod):
            try:
                with open(gomod, "r", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        if line.startswith("module "):
                            return line.split(None, 1)[1].strip()
            except OSError:
                pass
        return None

    def _norm(self, p: str):
        p = os.path.normpath(p).replace(os.sep, "/")
        return p[2:] if p.startswith("./") else p

    def _exists(self, cand: str):
        cand = self._norm(cand)
        return cand if cand in self.files else None

    def _try_exts(self, base: str):
        base = self._norm(base)
        hit = self._exists(base)
        if hit:
            return hit
        for ext in JS_EXTS + [".py", ".go", ".rs", ".rb", ".php"]:
            hit = self._exists(base + ext)
            if hit:
                return hit
        for ext in JS_EXTS:
            hit = self._exists(base + "/index" + ext)
            if hit:
                return hit
        for name in ("__init__.py", "mod.rs", "lib.rs"):
            hit = self._exists(base + "/" + name)
            if hit:
                return hit
        return None

    def resolve(self, spec: str, from_file: str, language: str):
        """Return (resolved_rel_path | None, external_name | None)."""
        spec = spec.strip().strip(QUOTE_CHARS)
        if not spec:
            return None, None
        here = os.path.dirname(from_file)

        # Relative paths (JS/TS/Python-dot/shell/C-include)
        if spec.startswith("."):
            if language == "python":
                dots = len(spec) - len(spec.lstrip("."))
                up = here
                for _ in range(dots - 1):
                    up = os.path.dirname(up)
                tail = spec[dots:].replace(".", "/")
                return self._try_exts(os.path.join(up, tail) if tail else up), None
            return self._try_exts(os.path.join(here, spec)), None

        if language == "python":
            tail = spec.replace(".", "/")
            for sr in SRC_ROOTS:
                hit = self._try_exts(os.path.join(sr, tail) if sr else tail)
                if hit:
                    return hit, None
            return None, spec.split(".")[0]

        if language in ("javascript", "typescript", "vue", "svelte"):
            if spec.startswith("@/") or spec.startswith("~/") or spec.startswith("#"):
                tail = spec[2:] if spec[1] == "/" else spec[1:]
                for sr in ("src", "app", "lib", ""):
                    hit = self._try_exts(os.path.join(sr, tail) if sr else tail)
                    if hit:
                        return hit, None
                return None, spec
            # Bare specifier that happens to match an internal path (monorepo/baseUrl).
            for sr in ("", "src", "lib", "app", "packages"):
                cand = os.path.join(sr, spec) if sr else spec
                if cand.replace(os.sep, "/").split("/")[0] in self.dirs or True:
                    hit = self._try_exts(cand)
                    if hit:
                        return hit, None
            ext_name = "/".join(spec.split("/")[:2]) if spec.startswith("@") else spec.split("/")[0]
            return None, ext_name

        if language == "go":
            if spec.startswith("mod::"):
                return None, None
            if self.go_module and spec.startswith(self.go_module):
                tail = spec[len(self.go_module):].lstrip("/")
                cand_dir = tail
                pkg_files = [f for f in self.files
                             if os.path.dirname(f).replace(os.sep, "/") == cand_dir and f.endswith(".go")]
                if pkg_files:
                    return sorted(pkg_files)[0], None
            if "." in spec.split("/")[0]:
                return None, "/".join(spec.split("/")[:3])
            return None, spec.split("/")[0]

        if language == "rust":
            if spec.startswith("mod::"):
                name = spec[5:]
                for cand in (os.path.join(here, name + ".rs"), os.path.join(here, name, "mod.rs")):
                    hit = self._exists(cand)
                    if hit:
                        return hit, None
                return None, None
            parts = [p for p in re.split(r"::", spec) if p and p not in ("{", "}")]
            if not parts:
                return None, None
            if parts[0] in ("crate", "self", "super"):
                tail = "/".join(parts[1:])
                for sr in ("src", ""):
                    hit = self._try_exts(os.path.join(sr, tail) if sr else tail)
                    if hit:
                        return hit, None
                return None, None
            if parts[0] == "std" or parts[0] == "core" or parts[0] == "alloc":
                return None, "std"
            return None, parts[0]

        if language in ("java", "kotlin", "scala", "csharp"):
            parts = spec.split(".")
            cls = parts[-1]
            path_hint = "/".join(parts).lower()
            for cand in self.by_stem.get(cls, []):
                if cand.lower().replace(os.sep, "/").endswith(path_hint + ".java") or \
                   cand.lower().replace(os.sep, "/").endswith(path_hint + ".kt") or \
                   cand.lower().replace(os.sep, "/").endswith(path_hint + ".scala") or \
                   cand.lower().replace(os.sep, "/").endswith(path_hint + ".cs"):
                    return cand, None
            if len(self.by_stem.get(cls, [])) == 1:
                return self.by_stem[cls][0], None
            return None, ".".join(parts[:2])

        if language in ("c", "cpp", "objc"):
            hit = self._try_exts(os.path.join(here, spec)) or self._exists(spec)
            if hit:
                return hit, None
            cands = self.by_basename.get(os.path.basename(spec), [])
            return (cands[0], None) if len(cands) == 1 else (None, spec)

        if language in ("ruby", "php", "shell"):
            hit = self._try_exts(os.path.join(here, spec)) or self._try_exts(spec)
            if hit:
                return hit, None
            for sr in ("lib", "app", "src", ""):
                hit = self._try_exts(os.path.join(sr, spec) if sr else spec)
                if hit:
                    return hit, None
            return None, spec.split("/")[0]

        return None, None


# --------------------------------------------------------------------------------------
# Graph metrics
# --------------------------------------------------------------------------------------

def pagerank(node_ids, out_edges, damping=0.85, iters=25):
    n = len(node_ids)
    if n == 0:
        return {}
    idx = {nid: i for i, nid in enumerate(node_ids)}
    outs = [[] for _ in range(n)]
    for src, targets in out_edges.items():
        if src not in idx:
            continue
        outs[idx[src]] = [idx[t] for t in targets if t in idx]
    rank = [1.0 / n] * n
    for _ in range(iters):
        nxt = [(1.0 - damping) / n] * n
        sink = 0.0
        for i in range(n):
            if not outs[i]:
                sink += rank[i]
                continue
            share = damping * rank[i] / len(outs[i])
            for j in outs[i]:
                nxt[j] += share
        if sink:
            add = damping * sink / n
            nxt = [v + add for v in nxt]
        rank = nxt
    return {nid: rank[idx[nid]] for nid in node_ids}


def find_cycles(node_ids, out_edges, limit=25):
    """Tarjan SCC, iterative (no recursion limit risk on big graphs)."""
    index = {}
    low = {}
    on_stack = set()
    stack = []
    result = []
    counter = [0]

    for root in node_ids:
        if root in index:
            continue
        work = [(root, iter(out_edges.get(root, ())))]
        index[root] = low[root] = counter[0]
        counter[0] += 1
        stack.append(root)
        on_stack.add(root)
        while work:
            node, it = work[-1]
            advanced = False
            for succ in it:
                if succ not in index:
                    index[succ] = low[succ] = counter[0]
                    counter[0] += 1
                    stack.append(succ)
                    on_stack.add(succ)
                    work.append((succ, iter(out_edges.get(succ, ()))))
                    advanced = True
                    break
                if succ in on_stack:
                    low[node] = min(low[node], index[succ])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index[node]:
                comp = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    comp.append(w)
                    if w == node:
                        break
                if len(comp) > 1:
                    result.append(sorted(comp))
    result.sort(key=len, reverse=True)
    return result[:limit]


# --------------------------------------------------------------------------------------
# Main scan
# --------------------------------------------------------------------------------------

def detect_frameworks(root: str, files):
    hints = []
    fset = set(files)

    def read(name):
        p = os.path.join(root, name)
        if os.path.exists(p):
            return read_text(p) or ""
        return ""

    pkg = read("package.json")
    if pkg:
        for name, label in [
            ('"next"', "Next.js"), ('"react"', "React"), ('"vue"', "Vue"),
            ('"svelte"', "Svelte"), ('"@angular/core"', "Angular"),
            ('"express"', "Express"), ('"fastify"', "Fastify"), ('"nest', "NestJS"),
            ('"vite"', "Vite"), ('"webpack"', "Webpack"), ('"jest"', "Jest"),
            ('"vitest"', "Vitest"), ('"tailwindcss"', "Tailwind"),
            ('"prisma"', "Prisma"), ('"electron"', "Electron"),
        ]:
            if name in pkg:
                hints.append(label)
    reqs = read("requirements.txt") + read("pyproject.toml") + read("setup.py") + read("Pipfile")
    if reqs:
        for name, label in [
            ("django", "Django"), ("flask", "Flask"), ("fastapi", "FastAPI"),
            ("torch", "PyTorch"), ("tensorflow", "TensorFlow"), ("pandas", "pandas"),
            ("sqlalchemy", "SQLAlchemy"), ("pydantic", "Pydantic"), ("celery", "Celery"),
            ("pytest", "pytest"), ("langchain", "LangChain"), ("transformers", "Transformers"),
        ]:
            if name in reqs.lower():
                hints.append(label)
    if "go.mod" in fset:
        hints.append("Go modules")
    if "Cargo.toml" in fset:
        hints.append("Cargo")
    if "pom.xml" in fset:
        hints.append("Maven")
    if any(f in fset for f in ("build.gradle", "build.gradle.kts")):
        hints.append("Gradle")
    if "Gemfile" in fset:
        hints.append("Bundler")
    if any(f.lower().startswith("dockerfile") for f in fset):
        hints.append("Docker")
    if any(f.startswith(".github/workflows/") for f in fset):
        hints.append("GitHub Actions")
    seen = []
    for h in hints:
        if h not in seen:
            seen.append(h)
    return seen


def entry_point_score(rel_path: str, extras: dict, language: str) -> int:
    score = 0
    low = rel_path.lower()
    base = os.path.basename(low)
    stem = os.path.splitext(base)[0]
    if stem in ("main", "__main__", "index", "app", "server", "cli", "manage", "wsgi", "asgi", "bootstrap"):
        score += 5
    if re.match(r"^(cmd|bin|scripts?)/", low):
        score += 3
    # Routes are context-verified; http_verbs alone are too weak a signal
    # (".get(" matches ordinary dict access), so they only reinforce routes.
    if extras.get("routes"):
        score += 3
        if extras.get("http_verbs"):
            score += 1
    if low.count("/") == 0:
        score += 1
    if re.search(r"(^|/)(tests?|__tests__)/", low):
        score -= 6
    return score


def git_commit(root: str) -> str:
    try:
        out = subprocess.run(["git", "-C", root, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=15)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def scan(root: str, max_files: int, want_calls: bool, symbols_for: int):
    root = os.path.abspath(root)
    started = time.time()

    candidates = git_tracked_files(root)
    discovery = "git"
    if candidates is None:
        candidates = walk_files(root)
        discovery = "walk"

    kept = []
    skipped_big = 0
    for rel in candidates:
        rel = rel.replace(os.sep, "/")
        kind, lang = classify(rel)
        if kind is None:
            continue
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            continue
        try:
            if os.path.getsize(full) > MAX_FILE_BYTES:
                skipped_big += 1
                continue
        except OSError:
            continue
        kept.append((rel, kind, lang))

    # Prefer real code when we must truncate.
    kept.sort(key=lambda t: (t[1] != "code", t[0].count("/"), t[0]))
    truncated = len(kept) > max_files
    if truncated:
        kept = kept[:max_files]

    all_rel = [k[0] for k in kept]
    resolver = Resolver(root, all_rel)

    files = {}
    for rel, kind, lang in kept:
        text = read_text(os.path.join(root, rel))
        if text is None:
            continue
        nlines = text.count("\n") + 1
        if nlines and len(text) / nlines > MAX_LINE_LEN_AVG and nlines < 50:
            continue  # minified-looking
        info = {"rel": rel, "kind": kind, "lang": lang, "loc": nlines, "bytes": len(text)}
        if kind == "code":
            ex = extract(lang, text, rel)
            info["raw_imports"] = ex["imports"]
            info["defs"] = ex["defs"]
            info["extras"] = ex["extras"]
            # The file's own words about itself — free, and covers ~94% of a
            # well-documented repo without any model involvement.
            info["doc"] = extract_doc(lang, text)
        else:
            info["raw_imports"] = []
            info["defs"] = []
            info["extras"] = {}
            if kind == "document":
                first = next((ln.strip("# ").strip() for ln in text.split("\n")[:20] if ln.strip()), "")
                info["extras"]["title"] = first[:120]
        info["text_cache"] = text if want_calls and kind == "code" else None
        files[rel] = info

    # ---- edges: imports -------------------------------------------------------------
    import_edges = []           # (src_rel, dst_rel)
    externals = Counter()
    external_users = defaultdict(set)
    unresolved = Counter()
    for rel, info in files.items():
        seen_targets = set()
        for spec in info["raw_imports"]:
            dst, ext = resolver.resolve(spec, rel, info["lang"])
            if dst and dst in files and dst != rel:
                if dst not in seen_targets:
                    seen_targets.add(dst)
                    import_edges.append((rel, dst))
            elif ext:
                externals[ext] += 1
                external_users[ext].add(rel)
            elif dst is None:
                unresolved[spec.split("/")[0][:40]] += 1
        info["imports_resolved"] = sorted(seen_targets)

    out_map = defaultdict(list)
    in_map = defaultdict(list)
    for s, d in import_edges:
        out_map[s].append(d)
        in_map[d].append(s)

    ranks = pagerank(list(files.keys()), out_map)
    cycles = find_cycles(list(files.keys()), out_map)

    # ---- importance & entry points --------------------------------------------------
    max_rank = max(ranks.values()) if ranks else 1.0
    for rel, info in files.items():
        fan_in = len(in_map.get(rel, []))
        fan_out = len(out_map.get(rel, []))
        info["fan_in"] = fan_in
        info["fan_out"] = fan_out
        norm_rank = ranks.get(rel, 0.0) / max_rank if max_rank else 0.0
        size_factor = min(info["loc"] / 400.0, 1.0)
        info["importance"] = round(
            0.55 * norm_rank + 0.25 * min(fan_in / 12.0, 1.0) + 0.20 * size_factor, 4)
        info["entry_score"] = entry_point_score(rel, info["extras"], info["lang"])
        info["layer"] = guess_layer(rel)

    entries = sorted(
        [r for r, i in files.items() if i["entry_score"] >= 3],
        key=lambda r: (-files[r]["entry_score"], -files[r]["importance"], r),
    )[:20]
    for r in entries:
        if files[r]["layer"] not in ("test", "docs"):
            files[r]["layer"] = "entry" if files[r]["entry_score"] >= 5 else files[r]["layer"]

    # ---- symbol nodes ---------------------------------------------------------------
    ranked_files = sorted(files.values(), key=lambda i: -i["importance"])
    symbol_hosts = {i["rel"] for i in ranked_files[:symbols_for]}
    symbols = {}   # sym_id -> record
    for rel in symbol_hosts:
        info = files[rel]
        tops = [d for d in info["defs"] if d.get("top")] or info["defs"]
        tops = sorted(tops, key=lambda d: -(d["end_line"] - d["line"]))[:24]
        for d in tops:
            sid = "sym:%s#%s:%d" % (rel, d["name"], d["line"])
            symbols[sid] = {
                "id": sid, "file": rel, "name": d["name"], "kind": d["kind"],
                "line": d["line"], "end_line": d["end_line"], "base": d.get("base"),
                "size": max(1, d["end_line"] - d["line"] + 1),
            }

    # ---- call edges (heuristic, bounded) -------------------------------------------
    call_edges = []
    if want_calls and symbols:
        by_name = defaultdict(list)
        for sid, s in symbols.items():
            nm = s["name"]
            if len(nm) >= 4 and nm.lower() not in CALL_STOPWORDS:
                by_name[nm].append(sid)
        unique_names = {nm: sids[0] for nm, sids in by_name.items() if len(sids) == 1}
        for rel, info in files.items():
            text = info.get("text_cache")
            if not text:
                continue
            stripper = COMMENT_STRIP["hash"] if info["lang"] in ("python", "ruby", "shell") \
                else COMMENT_STRIP["slash"]
            body = stripper.sub("", text)
            local_syms = sorted(
                [s for s in symbols.values() if s["file"] == rel],
                key=lambda s: s["line"])
            hits = set()
            for m in IDENT_RE.finditer(body):
                nm = m.group(0)
                target = unique_names.get(nm)
                if not target or symbols[target]["file"] == rel:
                    continue
                ln = body.count("\n", 0, m.start()) + 1
                caller = None
                for s in local_syms:
                    if s["line"] <= ln <= s["end_line"]:
                        caller = s["id"]
                source = caller or rel
                if (source, target) in hits:
                    continue
                hits.add((source, target))
                call_edges.append((source, target, ln))
            if len(call_edges) > 40000:
                break

    for info in files.values():
        info.pop("text_cache", None)

    stats = {
        "discovery": discovery,
        "files_considered": len(candidates),
        "files_indexed": len(files),
        "files_skipped_large": skipped_big,
        "truncated": truncated,
        "elapsed_sec": round(time.time() - started, 2),
    }
    return {
        "root": root, "files": files, "import_edges": import_edges,
        "symbols": symbols, "call_edges": call_edges, "externals": externals,
        "external_users": external_users, "unresolved": unresolved,
        "cycles": cycles, "entries": entries, "stats": stats,
        "in_map": in_map, "out_map": out_map,
    }


# --------------------------------------------------------------------------------------
# Graph assembly (schema-stable output)
# --------------------------------------------------------------------------------------

def build_graph(scanned: dict):
    root = scanned["root"]
    files = scanned["files"]
    nodes = []
    edges = []

    # module (directory) nodes
    dir_stats = defaultdict(lambda: {"files": 0, "loc": 0, "layers": Counter(), "langs": Counter()})
    for rel, info in files.items():
        d = os.path.dirname(rel) or "."
        st = dir_stats[d]
        st["files"] += 1
        st["loc"] += info["loc"]
        st["layers"][info["layer"]] += 1
        st["langs"][info["lang"]] += 1

    # Materialise EVERY ancestor directory, not just the ones holding files, so the
    # viewer can walk a real tree instead of a flat list. Without the intermediate
    # levels "src/" would not exist when only "src/api/core/" holds code.
    all_dirs = set(dir_stats)
    for d in list(dir_stats):
        if d == ".":
            continue
        parts = d.split("/")
        for i in range(1, len(parts)):
            all_dirs.add("/".join(parts[:i]))
    all_dirs.add(".")

    # Roll file counts/LOC up the tree so a collapsed parent reports its subtree.
    roll = {d: {"files": 0, "loc": 0, "layers": Counter(), "langs": Counter()}
            for d in all_dirs}
    for d, st in dir_stats.items():
        chain = ["."] if d == "." else \
            ["."] + ["/".join(d.split("/")[:i + 1]) for i in range(len(d.split("/")))]
        for anc in chain:
            if anc not in roll:
                continue
            roll[anc]["files"] += st["files"]
            roll[anc]["loc"] += st["loc"]
            roll[anc]["layers"].update(st["layers"])
            roll[anc]["langs"].update(st["langs"])

    def parent_of(d):
        if d == ".":
            return None
        return "/".join(d.split("/")[:-1]) or "."

    for d in sorted(all_dirs):
        st = roll[d]
        own = dir_stats.get(d)
        par = parent_of(d)
        nodes.append({
            "id": "mod:" + d,
            "type": "module",
            "name": (d.split("/")[-1] if d != "." else "(root)"),
            "filePath": d,
            "parent": ("mod:" + par) if par else None,
            "depth": 0 if d == "." else d.count("/") + 1,
            "layer": (st["layers"].most_common(1)[0][0] if st["layers"] else "other"),
            "loc": st["loc"],                       # subtree total
            "fileCount": st["files"],               # subtree total
            "ownFiles": own["files"] if own else 0,  # files directly inside
            "languages": [l for l, _ in st["langs"].most_common(4)],
            "summary": "",
            "tags": [],
        })
        # Directory -> subdirectory containment, so the tree is walkable.
        if par:
            edges.append({"source": "mod:" + par, "target": "mod:" + d,
                          "type": "contains", "weight": 1.0})

    for rel, info in sorted(files.items()):
        node_type = {"code": "file", "config": "config", "document": "document",
                     "infra": "config"}.get(info["kind"], "file")
        nodes.append({
            "id": "file:" + rel,
            "type": node_type,
            "name": os.path.basename(rel),
            "filePath": rel,
            "module": "mod:" + (os.path.dirname(rel) or "."),
            "language": info["lang"],
            "layer": info["layer"],
            "loc": info["loc"],
            "fanIn": info["fan_in"],
            "fanOut": info["fan_out"],
            "importance": info["importance"],
            "isEntry": rel in scanned["entries"],
            "defCount": len(info["defs"]),
            "routes": info["extras"].get("routes", [])[:8],
            "httpVerbs": info["extras"].get("http_verbs", []),
            "title": info["extras"].get("title", ""),
            # summary is pre-filled from the source's own docstring; the agent's
            # enrich.json overrides it where it can say something better.
            "doc": info.get("doc", ""),
            "symbols": [d["name"] for d in info["defs"][:14]],
            "summary": "",
            "tags": [],
        })
        edges.append({"source": "mod:" + (os.path.dirname(rel) or "."),
                      "target": "file:" + rel, "type": "contains", "weight": 1.0})

    for sid, s in sorted(scanned["symbols"].items()):
        nodes.append({
            "id": sid,
            "type": {"class": "class", "impl": "class", "type": "class", "schema": "schema",
                     "table": "table", "service": "service", "resource": "resource"}
                    .get(s["kind"], "function"),
            "name": s["name"],
            "filePath": s["file"],
            "module": "mod:" + (os.path.dirname(s["file"]) or "."),
            "lineRange": [s["line"], s["end_line"]],
            "kind": s["kind"],
            "loc": s["size"],
            "layer": files[s["file"]]["layer"],
            "summary": "",
            "tags": [],
        })
        edges.append({"source": "file:" + s["file"], "target": sid,
                      "type": "contains", "weight": 1.0})
        if s.get("base"):
            edges.append({"source": sid, "target": "ref:" + s["base"],
                          "type": "inherits", "weight": 0.6, "unresolved": True})

    for s, d in scanned["import_edges"]:
        edges.append({"source": "file:" + s, "target": "file:" + d,
                      "type": "imports", "weight": 1.0})

    for src, dst, line in scanned["call_edges"]:
        edges.append({
            "source": src if src.startswith("sym:") else "file:" + src,
            "target": dst, "type": "calls", "weight": 0.5, "line": line,
        })

    # external dependency nodes (capped: only ones actually used more than once or by many files)
    ext_items = sorted(scanned["externals"].items(), key=lambda kv: -kv[1])[:60]
    for name, count in ext_items:
        nodes.append({
            "id": "ext:" + name, "type": "external", "name": name, "layer": "external",
            "usedBy": len(scanned["external_users"][name]), "importCount": count,
            "summary": "", "tags": [],
        })
        for user in sorted(scanned["external_users"][name])[:40]:
            edges.append({"source": "file:" + user, "target": "ext:" + name,
                          "type": "depends_on", "weight": 0.3})

    # Drop edges pointing at unresolved inheritance refs that never became nodes.
    node_ids = {n["id"] for n in nodes}
    edges = [e for e in edges if e["source"] in node_ids and e["target"] in node_ids]

    lang_counter = Counter()
    for info in files.values():
        if info["kind"] == "code":
            lang_counter[info["lang"]] += 1

    layers = []
    for lid in LAYER_ORDER:
        member_ids = [n["id"] for n in nodes if n.get("layer") == lid]
        if member_ids:
            layers.append({"id": lid, "name": LAYER_LABELS.get(lid, lid.title()),
                           "description": "", "nodeIds": member_ids})

    graph = {
        "version": SCHEMA_VERSION,
        "kind": "codebase",
        "project": {
            "name": os.path.basename(root) or root,
            "root": root,
            "languages": [l for l, _ in lang_counter.most_common()],
            "frameworks": detect_frameworks(root, list(files.keys())),
            "description": "",
            "analyzedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "gitCommitHash": git_commit(root),
            "totalLoc": sum(i["loc"] for i in files.values()),
        },
        "stats": scanned["stats"],
        "nodes": nodes,
        "edges": edges,
        "layers": layers,
        "cycles": [["file:" + r for r in comp] for comp in scanned["cycles"]],
        "tour": [],
    }
    return graph


# --------------------------------------------------------------------------------------
# Digest (what the agent actually reads)
# --------------------------------------------------------------------------------------

def build_digest(scanned: dict, graph: dict, top_n: int = 45) -> str:
    files = scanned["files"]
    p = graph["project"]
    L = []
    A = L.append

    A("# codegraph digest: %s" % p["name"])
    A("")
    A("> Stage-1 deterministic scan. Read this instead of graph.json, then write enrich.json.")
    A("")
    A("- **Root**: `%s`" % p["root"])
    A("- **Commit**: `%s`" % (p["gitCommitHash"] or "n/a"))
    A("- **Indexed**: %d files, %s LOC (discovery: %s%s)" % (
        scanned["stats"]["files_indexed"], f"{p['totalLoc']:,}",
        scanned["stats"]["discovery"],
        ", TRUNCATED — raise --max-files" if scanned["stats"]["truncated"] else ""))
    A("- **Languages**: %s" % (", ".join(
        "%s (%d)" % (l, sum(1 for i in files.values() if i["lang"] == l))
        for l in p["languages"][:8]) or "n/a"))
    A("- **Frameworks detected**: %s" % (", ".join(p["frameworks"][:12]) or "none detected"))
    A("- **Graph**: %d nodes, %d edges" % (len(graph["nodes"]), len(graph["edges"])))
    A("")

    A("## Entry points (start reading here)")
    if scanned["entries"]:
        for rel in scanned["entries"][:12]:
            i = files[rel]
            extra = []
            if i["extras"].get("routes"):
                extra.append("routes: " + ", ".join(i["extras"]["routes"][:5]))
            if i["extras"].get("http_verbs"):
                extra.append("http: " + ",".join(i["extras"]["http_verbs"]))
            A("- `%s` (%s, %d LOC, fan-in %d)%s" % (
                rel, i["lang"], i["loc"], i["fan_in"],
                " — " + "; ".join(extra) if extra else ""))
    else:
        A("- none detected by heuristics")
    A("")

    A("## Directory map (files / LOC / dominant layer)")
    dirs = defaultdict(lambda: [0, 0, Counter()])
    for rel, i in files.items():
        d = os.path.dirname(rel) or "."
        dirs[d][0] += 1
        dirs[d][1] += i["loc"]
        dirs[d][2][i["layer"]] += 1
    shown = sorted(dirs.items(), key=lambda kv: -kv[1][1])[:40]
    for d, (nf, loc, layers) in sorted(shown):
        A("- `%s/` — %d files, %d LOC, mostly **%s**" % (
            d, nf, loc, layers.most_common(1)[0][0]))
    if len(dirs) > 40:
        A("- ... %d more directories" % (len(dirs) - 40))
    A("")

    A("## Most important files (PageRank on imports + fan-in + size)")
    A("")
    A("| node id | LOC | in | out | layer | defs |")
    A("|---|---|---|---|---|---|")
    ranked = sorted(files.values(), key=lambda i: -i["importance"])[:top_n]
    for i in ranked:
        A("| `file:%s` | %d | %d | %d | %s | %s |" % (
            i["rel"], i["loc"], i["fan_in"], i["fan_out"], i["layer"],
            ", ".join(d["name"] for d in i["defs"][:5]) or "—"))
    A("")

    if scanned["cycles"]:
        A("## Dependency cycles (refactor candidates)")
        for comp in scanned["cycles"][:8]:
            A("- %d files: %s" % (len(comp), ", ".join("`%s`" % c for c in comp[:6]) +
                                  (" ..." if len(comp) > 6 else "")))
        A("")

    A("## Top external dependencies")
    top_ext = sorted(scanned["externals"].items(), key=lambda kv: -kv[1])[:25]
    A(", ".join("`%s` (%d)" % (n, c) for n, c in top_ext) or "none")
    A("")

    A("## Heuristic layer assignment (override in enrich.json when wrong)")
    layer_counts = Counter(i["layer"] for i in files.values())
    for lid in LAYER_ORDER:
        if layer_counts.get(lid):
            A("- **%s** (`%s`): %d files" % (LAYER_LABELS.get(lid, lid), lid, layer_counts[lid]))
    A("")

    A("## Your job (stage 2)")
    A("")
    A("Write `enrich.json` next to this digest:")
    A("")
    A("```json")
    A("{")
    A('  "project": { "description": "1-3 sentences: what this codebase IS and does" },')
    A('  "nodes": {')
    A('    "file:path/to/file.ts": { "summary": "plain-English what+why, 1-2 sentences",')
    A('                              "layer": "service", "tags": ["auth"] }')
    A("  },")
    A('  "layers": { "service": "what this layer means in THIS project" },')
    A('  "tours": [')
    A('    { "title": "Request lifecycle", "description": "why this tour matters",')
    A('      "steps": [ { "nodeId": "file:src/index.ts", "note": "why this step matters" } ] }')
    A("  ]")
    A("}")
    A("```")
    A("")
    A("Rules: only use node ids that exist above; summarize the top files first; "
      "1 tour minimum, 3-6 steps each; never invent files.")
    return "\n".join(L)


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="scan.py", description="Deterministic codebase -> structural graph (codegraph stage 1)")
    ap.add_argument("root", nargs="?", default=".", help="repository root (default: .)")
    ap.add_argument("-o", "--out", default=".codegraph", help="output directory (default: .codegraph)")
    ap.add_argument("--max-files", type=int, default=4000, help="cap indexed files (default: 4000)")
    ap.add_argument("--symbols-for", type=int, default=250,
                    help="extract symbol nodes for the N most important files (default: 250)")
    ap.add_argument("--no-calls", action="store_true", help="skip heuristic cross-file call edges")
    ap.add_argument("--digest-top", type=int, default=45, help="rows in the digest importance table")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.root):
        print("error: not a directory: %s" % args.root, file=sys.stderr)
        return 2

    scanned = scan(args.root, args.max_files, not args.no_calls, args.symbols_for)
    if not scanned["files"]:
        print("error: no source files found under %s" % args.root, file=sys.stderr)
        return 1

    graph = build_graph(scanned)
    digest = build_digest(scanned, graph, args.digest_top)

    outdir = args.out if os.path.isabs(args.out) else os.path.join(os.path.abspath(args.root), args.out)
    os.makedirs(outdir, exist_ok=True)
    gpath = os.path.join(outdir, "graph.json")
    dpath = os.path.join(outdir, "digest.md")
    with open(gpath, "w", encoding="utf-8") as fh:
        json.dump(graph, fh, indent=1, sort_keys=False)
    with open(dpath, "w", encoding="utf-8") as fh:
        fh.write(digest + "\n")

    if not args.quiet:
        s = scanned["stats"]
        print("codegraph scan complete in %ss" % s["elapsed_sec"])
        print("  indexed   : %d files (%s LOC)" % (s["files_indexed"], f"{graph['project']['totalLoc']:,}"))
        print("  graph     : %d nodes, %d edges" % (len(graph["nodes"]), len(graph["edges"])))
        print("  cycles    : %d" % len(graph["cycles"]))
        print("  languages : %s" % ", ".join(graph["project"]["languages"][:6]))
        print("  graph.json: %s" % gpath)
        print("  digest.md : %s   <- read this next" % dpath)
        if s["truncated"]:
            print("  WARNING: file cap hit; rerun with --max-files %d" % (args.max_files * 3))
    return 0


if __name__ == "__main__":
    sys.exit(main())

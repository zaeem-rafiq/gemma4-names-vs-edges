"""Study B: read the main competition's tasks, official graphs and repository snapshots.

The competition data is untrusted input: nothing in it is executed or imported. Files are read as
text and parsed with `ast`; snapshot archives are read member by member (`read_snapshot_py`), never
extracted with their own paths, and links, devices, absolute paths and ".." are skipped.

Official graph format (checked on the competition data on 9 Nov 2026): node-link JSON with
`directed`, `multigraph`, `graph` {repo_name}, `nodes` [{id, name, text}] and `edges`
[{source, target, type, key}]; every edge type is "calls" and every non-self edge has its reverse,
so the graph is read as undirected (`neighbours`). Node ids are dotted qualified names
(package.module.Class.method); there is no file path or node-kind field, and some source roots are
dropped from the names (for example files under docs_src/).

Node index (`SnapshotIndex`). Every Python file of the snapshot is parsed; its functions (module
level and in classes, at any class depth, also inside module- or class-level if/try/with blocks,
the same rule as ngraph.extract) and its classes get local qualified names. The module name of a
file is the candidate, among the dotted path with the leading components dropped one at a time
(after the src-layout rule of ngraph.extract), under which the most of the file's local names are
official node ids; ties go to the longest candidate; a file with no match has no module. An
official node id then maps to (path, first line including decorators, last line, kind).

Library functions (the Study B candidates and gold): official nodes of kind "function" whose file is
one of the files that ngraph.extract.select_files keeps for the repository (the main package,
without tests, docs, scripts, examples, benchmarks and vendored code), the same rule as the Study A
graphs.
"""

from __future__ import annotations

import ast
import json
import os
import posixpath
import tarfile
from collections import defaultdict

from ngraph.extract import Extractor, is_excluded, module_name_for, select_files, src_is_package

OFFICIAL_VERSION = "0.1.0"
MAX_MEMBER_BYTES = 2_000_000
KEEP_BASENAMES = ("pyproject.toml", "setup.cfg", "setup.py")


# ----------------------------------------------------------------------------- tasks and graphs
def load_tasks(path: str) -> list[dict]:
    """tasks.jsonl -> list of task dicts (file order). Duplicate instance ids are an error."""
    out, seen = [], set()
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            if not line.strip():
                continue
            t = json.loads(line)
            if not isinstance(t, dict) or "instance_id" not in t:
                raise ValueError(f"{path}:{i}: not a task object")
            if t["instance_id"] in seen:
                raise ValueError(f"{path}:{i}: duplicate instance_id {t['instance_id']}")
            seen.add(t["instance_id"])
            out.append(t)
    return out


def short_repo(task: dict) -> str:
    """Short repository name used in the official file names: the instance id up to its last "_"."""
    return task["instance_id"].rsplit("_", 1)[0]


def graph_name(task: dict) -> str:
    return f"{short_repo(task)}_{task['base_commit']}"


def load_graph(path: str) -> dict:
    """Official node-link graph -> {"name", "nodes": {id: text}, "edges": [(s, t, type)], "stats"}.
    Duplicate (source, target, type) edges are kept once; self-loops are kept (and counted)."""
    with open(path, encoding="utf-8") as fh:
        g = json.load(fh)
    nodes = {}
    for n in g["nodes"]:
        nid = n["id"]
        if not isinstance(nid, str):
            raise ValueError(f"{path}: non-string node id {nid!r}")
        nodes[nid] = n.get("text") or ""
    links = g.get("edges", g.get("links"))
    seen, edges, dup, missing = set(), [], 0, 0
    for e in links:
        s, t, ty = e["source"], e["target"], e.get("type", "calls")
        if s not in nodes or t not in nodes:
            missing += 1
            continue
        k = (s, t, ty)
        if k in seen:
            dup += 1
            continue
        seen.add(k)
        edges.append(k)
    pairs = {(s, t) for s, t, _ in edges if s != t}
    stats = {"nodes": len(nodes), "edges": len(edges), "duplicate_edges_dropped": dup,
             "edges_with_missing_endpoint": missing, "self_loops": sum(s == t for s, t, _ in edges),
             "edge_types": sorted({ty for _, _, ty in edges}),
             "mirrored": all((t, s) in pairs for s, t in pairs),
             "directed_flag": g.get("directed"), "multigraph_flag": g.get("multigraph")}
    return {"name": (g.get("graph") or {}).get("repo_name"), "nodes": nodes, "edges": edges, "stats": stats}


def neighbours(edges) -> dict:
    """Undirected neighbour sets without self-loops."""
    nb = defaultdict(set)
    for s, t, _ in edges:
        if s != t:
            nb[s].add(t)
            nb[t].add(s)
    return nb


# ----------------------------------------------------------------------------- snapshots
def _safe_member(m: tarfile.TarInfo) -> str | None:
    """Normalised relative path of a regular-file member, or None for anything unsafe."""
    if not m.isfile():
        return None
    name = m.name.replace("\\", "/")
    while name.startswith("./"):
        name = name[2:]
    if not name or name.startswith("/") or ".." in name.split("/"):
        return None
    norm = posixpath.normpath(name)
    if norm.startswith("../") or norm == "..":
        return None
    return norm


def wanted(rel: str) -> bool:
    parts = rel.split("/")
    if ".git" in parts[:-1]:
        return False
    return rel.endswith(".py") or parts[-1] in KEEP_BASENAMES


def read_snapshot_py(tgz_path: str, prefix: str | None = None, max_bytes: int = MAX_MEMBER_BYTES) -> tuple[dict, dict]:
    """Python files (and packaging files) of a snapshot archive as {relative path: bytes}.
    With `prefix` (a bundle holding several snapshots under "<instance_id>/"), only members under
    that folder are read and the prefix is removed. Returns (files, skipped counts by reason)."""
    files, skipped = {}, defaultdict(int)
    with tarfile.open(tgz_path, "r:*") as tf:
        for m in tf:
            rel = _safe_member(m)
            if rel is None:
                skipped["not a safe regular file"] += 1
                continue
            if prefix is not None:
                if not rel.startswith(prefix.rstrip("/") + "/"):
                    continue
                rel = rel[len(prefix.rstrip("/")) + 1:]
            if not wanted(rel):
                continue
            if m.size > max_bytes:
                skipped["over size limit"] += 1
                continue
            fh = tf.extractfile(m)
            if fh is None:
                skipped["unreadable"] += 1
                continue
            files[rel] = fh.read()
    return files, dict(skipped)


def write_tree(files: dict, root: str) -> None:
    """Write {relative path: bytes} under root (paths were checked by read_snapshot_py)."""
    root = os.path.realpath(root)
    for rel, data in sorted(files.items()):
        dest = os.path.realpath(os.path.join(root, rel))
        if not dest.startswith(root + os.sep):
            raise ValueError(f"unsafe path {rel!r}")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(data)


# ----------------------------------------------------------------------------- text
def read_text(path: str) -> str | None:
    """A file as text: UTF-8 with an optional byte-order mark, undecodable bytes replaced."""
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8-sig", errors="replace")


def source_lines(text: str) -> list[str]:
    """Lines as `ast` numbers them: only \r\n, \r and \n end a line (str.splitlines also splits on form
    feeds, U+2028 and others, which would shift every later line)."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


# ----------------------------------------------------------------------------- node index
def local_spans(source: str) -> list[tuple[str, int, int, str]]:
    """(local qualified name, first line incl. decorators, last line, kind) of every function and
    class at node level (ngraph.extract's rule: module level and class bodies at any depth,
    descending into if/try/with blocks; nothing inside a function)."""
    tree = ast.parse(source)
    out = []

    def walk(body, prefix):
        for st in Extractor._toplevel_stmts(body):
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
                first = min([st.lineno] + [d.lineno for d in st.decorator_list])
                out.append((prefix + st.name, first, st.end_lineno, "function"))
            elif isinstance(st, ast.ClassDef):
                first = min([st.lineno] + [d.lineno for d in st.decorator_list])
                out.append((prefix + st.name, first, st.end_lineno, "class"))
                walk(st.body, prefix + st.name + ".")

    walk(tree.body, "")
    return out


def module_candidates(rel: str, strip_src: bool) -> list[str]:
    """The file's dotted module path and every shorter one with leading components dropped."""
    mod, _ = module_name_for(rel, strip_src)
    parts = mod.split(".") if mod else []
    return [".".join(parts[i:]) for i in range(len(parts))]


class SnapshotIndex:
    """Maps official node ids to files and line spans of a snapshot on disk (see the module docstring)."""

    def __init__(self, root: str, node_ids, files: list[str] | None = None):
        self.root = root
        ids = set(node_ids)
        if files is None:
            files = []
            for d, dirs, fs in os.walk(root):
                dirs[:] = sorted(x for x in dirs if x != ".git")
                for f in sorted(fs):
                    if f.endswith(".py"):
                        files.append(os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/"))
        self.files = sorted(files)
        strip = not src_is_package(root, self.files)
        self.module = {}            # path -> module name used by the official graph
        self.node = {}              # official id -> {"path","lineno","end_lineno","kind","module"}
        self.parse_errors = []
        self.ambiguous = []         # ids claimed by more than one file
        claimed = defaultdict(list)
        for rel in self.files:
            src = self.read(rel)
            if src is None:
                continue
            try:
                spans = local_spans(src)
            except (SyntaxError, ValueError) as exc:
                self.parse_errors.append(f"{rel}: {type(exc).__name__}")
                continue
            best, best_n = None, 0
            for cand in module_candidates(rel, strip):
                n = sum(f"{cand}.{name}" in ids for name, _, _, _ in spans)
                if n > best_n or (n == best_n and n > 0 and best is not None and len(cand) > len(best)):
                    best, best_n = cand, n
            if best is None:
                continue
            self.module[rel] = best
            for name, a, b, kind in spans:
                qn = f"{best}.{name}"
                if qn in ids:
                    claimed[qn].append({"path": rel, "lineno": a, "end_lineno": b, "kind": kind, "module": best})
        self.merged = 0
        for qn, recs in claimed.items():
            if len({r["path"] for r in recs}) == 1:
                # several definitions in one file (property getter and setter, @overload stubs,
                # if/else or try/except variants): one span from the first to the last
                r = dict(recs[0])
                r["lineno"] = min(x["lineno"] for x in recs)
                r["end_lineno"] = max(x["end_lineno"] for x in recs)
                if any(x["kind"] == "function" for x in recs):
                    r["kind"] = "function"
                self.merged += len(recs) > 1
                self.node[qn] = r
            else:
                self.ambiguous.append(qn)
        self._lines = {}

    def read(self, rel: str) -> str | None:
        return read_text(os.path.join(self.root, rel))

    def lines(self, rel: str) -> list[str]:
        if rel not in self._lines:
            txt = self.read(rel)
            self._lines[rel] = source_lines(txt) if txt is not None else []
        return self._lines[rel]

    def source(self, nid: str) -> str:
        r = self.node[nid]
        return "\n".join(self.lines(r["path"])[r["lineno"] - 1: r["end_lineno"]])

    def module_of(self, rel: str) -> str | None:
        return self.module.get(rel)

    def stats(self, node_ids) -> dict:
        ids = list(node_ids)
        return {"files": len(self.files), "files_with_module": len(self.module),
                "nodes_located": sum(i in self.node for i in ids), "nodes": len(ids),
                "ambiguous": len(self.ambiguous), "merged_same_file": self.merged,
                "parse_errors": len(self.parse_errors)}


def library_files(root: str) -> tuple[list[str], dict]:
    """The files ngraph.extract.select_files keeps (main package, non-test), as for Study A."""
    files, info = select_files(root)
    return sorted(f.replace(os.sep, "/") for f in files), info


def library_functions(index: SnapshotIndex, lib_files) -> list[str]:
    lib = set(lib_files)
    return sorted(nid for nid, r in index.node.items()
                  if r["kind"] == "function" and r["path"] in lib and not is_excluded(r["path"]))


def node_records(index: SnapshotIndex, ids=None) -> list[dict]:
    """Node dicts in the shape ngraph.localize expects (id, module, path, lineno, end_lineno)."""
    ids = sorted(index.node) if ids is None else ids
    return [{"id": i, **index.node[i]} for i in ids if i in index.node]



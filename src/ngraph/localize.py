"""Study B task tools: gold functions from a patch, BM25 candidate pools, issue anchors, strata.

Rules (pre-registration, section 4, made concrete here; every constant is a pre-registration item):

* Gold: the innermost enclosing non-test function of each changed line at the base commit.
  Removed lines are located in the base file and added lines in the patched file. Functions are
  graph nodes as ngraph.extract defines them (module-level functions and class methods, also
  inside module- or class-level if/try/with blocks), so a line in a nested function counts for
  the node around it and a line outside every node counts for none. A span starts at the first
  decorator. Functions that the patch creates do not exist at the base commit and are not gold.
* Candidate pool: BM25 (k1 = 1.2, b = 0.75, idf = ln(1 + (N - df + 0.5) / (df + 0.5))) over
  library functions. Document = qualified name + function source; query = the set of tokens of
  the issue text. Tokens: identifiers and numbers, split on underscores and case changes, lower
  case; a multi-part identifier is also kept whole; one-character parts and a short English
  stop list are dropped. Top 10, ties broken by node id. If no gold function is in the top 10,
  the best-ranked gold function replaces rank 10 and the task is flagged "injected".
* Anchors: identifier-shaped strings in the issue that match exactly one graph node of degree
  50 or less. Mentions: identifiers inside inline code spans, dotted paths, CamelCase,
  snake_case and _private names anywhere, and traceback frames. A leading "self." or "cls." is
  dropped; outside inline code the bare name left must itself look like an identifier. Matching, first tier with any match wins and must be unique: (1) the mention equals
  the node id or its trailing components; (2) for dotted mentions, the first component equals
  the node's package and the remaining components are the node's trailing components.
  Traceback frames match by module path and function name (frame line inside the node span
  breaks ties). Anchors are ordered by first mention.
* Strata: S0 an anchor is gold; S1 gold is one hop from an anchor; S2 two hops; S3 other
  (including tasks without anchors; "anchored" is reported separately). Hops ignore direction.
"""

from __future__ import annotations

import ast
import math
import re
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field

from ngraph.extract import Extractor, is_excluded

K1, B = 1.2, 0.75
POOL_K = 10
MAX_ANCHOR_DEGREE = 50
STOPWORDS = frozenset(
    "a an and are as at be been but by can do does for from has have if in into is it its "
    "not no of on or so such than that the then there these they this to was were when which "
    "will with would you we our your".split())

# ----------------------------------------------------------------------------- tokens and BM25
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+")
_PART = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")


def code_tokens(text: str) -> list[str]:
    out = []
    for w in _WORD.findall(text):
        parts = [p.lower() for seg in w.split("_") for p in _PART.findall(seg)]
        whole = w.strip("_").lower()
        if len(parts) > 1 and whole:
            out.append(whole)
        out.extend(p for p in parts if len(p) > 1 and p not in STOPWORDS)
    return out


class BM25:
    """Okapi BM25 over a fixed document set (inverted index; deterministic)."""

    def __init__(self, docs: dict, k1: float = K1, b: float = B):
        self.k1, self.b = k1, b
        self.ids = sorted(docs)
        tfs = [Counter(code_tokens(docs[i])) for i in self.ids]
        self.dl = [sum(c.values()) for c in tfs]
        n = len(self.ids)
        self.avgdl = (sum(self.dl) / n) if n else 1.0
        self.post = defaultdict(list)
        for d, c in enumerate(tfs):
            for t, f in c.items():
                self.post[t].append((d, f))
        self.idf = {t: math.log(1 + (n - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self.post.items()}

    def scores(self, query: str) -> dict:
        acc = [0.0] * len(self.ids)
        for t in sorted(set(code_tokens(query))):
            p = self.post.get(t)
            if not p:
                continue
            idf = self.idf[t]
            for d, f in p:
                norm = self.k1 * (1 - self.b + self.b * self.dl[d] / self.avgdl)
                acc[d] += idf * f * (self.k1 + 1) / (f + norm)
        return dict(zip(self.ids, acc))


def rank(scores: dict) -> list:
    return sorted(scores, key=lambda i: (-scores[i], i))


def candidate_pool(scores: dict, gold, k: int = POOL_K) -> dict:
    """Top-k by score (ties by id), with the pre-registered gold injection at rank k."""
    ranked = rank(scores)
    pos = {x: r + 1 for r, x in enumerate(ranked)}
    gold = sorted(set(gold))
    gold_ranks = {g: pos[g] for g in gold if g in pos}
    pool = ranked[:k]
    injected = False
    if gold_ranks and not any(g in pool for g in gold_ranks):
        best = min(gold_ranks, key=lambda g: (gold_ranks[g], g))
        pool = pool[: k - 1] + [best]
        injected = True
    return {"pool": pool, "injected": injected, "gold_ranks": gold_ranks,
            "gold_missing": [g for g in gold if g not in pos],
            "gold_in_pool": [g for g in pool if g in gold_ranks]}


def function_documents(nodes, read_file) -> dict:
    """node id -> qualified name + source lines [lineno, end_lineno] of the node's file."""
    cache, docs = {}, {}
    for n in nodes:
        path = n.get("path")
        if path not in cache:
            txt = read_file(path)
            cache[path] = txt.splitlines() if txt is not None else None
        lines = cache[path]
        body = "\n".join(lines[n["lineno"] - 1: n["end_lineno"]]) if lines and n.get("lineno") else ""
        docs[n["id"]] = n["id"] + "\n" + body
    return docs


# ----------------------------------------------------------------------------- gold from a patch
@dataclass
class FilePatch:
    old_path: str | None
    new_path: str | None
    hunks: list = field(default_factory=list)  # (old_start, old_len, new_start, new_len, lines)


_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _strip_prefix(p: str) -> str | None:
    p = p.split("\t")[0].strip()
    if p == "/dev/null":
        return None
    return p[2:] if p[:2] in ("a/", "b/") else p


def parse_unified_diff(text: str) -> list[FilePatch]:
    files, cur, i = [], None, 0
    lines = text.splitlines()
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("--- ") and i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
            cur = FilePatch(_strip_prefix(ln[4:]), _strip_prefix(lines[i + 1][4:]))
            files.append(cur)
            i += 2
            continue
        m = _HUNK.match(ln)
        if m and cur is not None:
            os_, ol, ns, nl = (int(m.group(1)), int(m.group(2) or 1), int(m.group(3)), int(m.group(4) or 1))
            body, i = [], i + 1
            o_left, n_left = ol, nl
            while i < len(lines) and (o_left > 0 or n_left > 0):
                s = lines[i]
                if s.startswith("\\"):
                    i += 1
                    continue
                tag = s[:1] if s else " "
                if tag not in (" ", "-", "+"):
                    break
                body.append((tag, s[1:]))
                o_left -= tag in (" ", "-")
                n_left -= tag in (" ", "+")
                i += 1
            cur.hunks.append((os_, ol, ns, nl, body))
            continue
        i += 1
    return files


def changed_lines(fp: FilePatch) -> tuple[set, set]:
    """(removed line numbers in the old file, added line numbers in the new file)."""
    old, new = set(), set()
    for os_, _, ns, _, body in fp.hunks:
        o, n = os_, ns
        for tag, _ in body:
            if tag == " ":
                o += 1
                n += 1
            elif tag == "-":
                old.add(o)
                o += 1
            else:
                new.add(n)
                n += 1
    return old, new


def apply_patch(old_text: str, fp: FilePatch) -> str:
    """Apply one file's hunks; raises ValueError if a context or removed line does not match."""
    src = old_text.splitlines()
    out, pos = [], 0
    for os_, ol, _, _, body in fp.hunks:
        start = os_ - 1 if ol > 0 else os_
        if start < pos:
            raise ValueError("overlapping hunks")
        out.extend(src[pos:start])
        pos = start
        for tag, s in body:
            if tag in (" ", "-"):
                if pos >= len(src) or src[pos] != s:
                    raise ValueError(f"patch does not apply at line {pos + 1}")
                pos += 1
                if tag == " ":
                    out.append(s)
            else:
                out.append(s)
    out.extend(src[pos:])
    return "\n".join(out) + ("\n" if old_text.endswith("\n") or not old_text else "")


def function_spans(source: str) -> list[tuple[str, int, int]]:
    """(local qualified name, first line incl. decorators, last line) of every node-level function."""
    tree = ast.parse(source)
    spans = []

    def walk(body, prefix):
        for st in Extractor._toplevel_stmts(body):
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
                first = min([st.lineno] + [d.lineno for d in st.decorator_list])
                spans.append((prefix + st.name, first, st.end_lineno))
            elif isinstance(st, ast.ClassDef):
                walk(st.body, prefix + st.name + ".")

    walk(tree.body, "")
    return spans


def innermost(spans, line: int) -> str | None:
    best = None
    for name, a, b in spans:
        if a <= line <= b and (best is None or b - a < best[2] - best[1]):
            best = (name, a, b)
    return best[0] if best else None


def gold_functions(patch: str, read_old, module_of, node_ids) -> dict:
    """Map a patch to gold node ids.

    read_old(path) -> base-commit text or None; module_of(path) -> module name or None;
    node_ids: the graph's node ids. Test and other excluded files (ngraph.extract.is_excluded)
    are skipped.
    """
    node_ids = set(node_ids)
    gold, rows = set(), []
    for fp in parse_unified_diff(patch):
        path = fp.old_path or fp.new_path
        row = {"path": path, "skipped": None, "lines": 0, "mapped": 0, "new_functions": [], "not_in_graph": []}
        rows.append(row)
        if not path or not path.endswith(".py"):
            row["skipped"] = "not a Python file"
            continue
        if is_excluded(path):
            row["skipped"] = "test or excluded file"
            continue
        if fp.old_path is None:
            row["skipped"] = "file created by the patch"
            continue
        old_text = read_old(fp.old_path)
        mod = module_of(fp.old_path)
        if old_text is None or mod is None:
            row["skipped"] = "file or module not found at base"
            continue
        old_lines, new_lines = changed_lines(fp)
        try:
            old_spans = function_spans(old_text)
            new_spans = function_spans(apply_patch(old_text, fp)) if fp.new_path else []
        except (SyntaxError, ValueError) as exc:
            row["skipped"] = f"{type(exc).__name__}: {exc}"
            continue
        old_names = {n for n, _, _ in old_spans}
        hits = [innermost(old_spans, ln) for ln in sorted(old_lines)]
        new_hits = [innermost(new_spans, ln) for ln in sorted(new_lines)]
        row["new_functions"] = sorted({h for h in new_hits if h and h not in old_names})
        hits += [h for h in new_hits if h in old_names]
        row["lines"] = len(old_lines) + len(new_lines)
        for h in hits:
            if h is None:
                continue
            qn = f"{mod}.{h}"
            if qn in node_ids:
                gold.add(qn)
                row["mapped"] += 1
            elif qn not in row["not_in_graph"]:
                row["not_in_graph"].append(qn)
    return {"gold": sorted(gold), "files": rows}


# ----------------------------------------------------------------------------- anchors and strata
_INLINE_CODE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
_DOTTED = re.compile(r"(?<![\w.])[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+")
_IDENT = re.compile(r"(?<![\w.])[A-Za-z_]\w*(?!\w|\.[A-Za-z_])")
_FRAME = re.compile(r'File "([^"\n]+)", line (\d+), in ([A-Za-z_]\w*)')


def _identifier_shaped(w: str) -> bool:
    core = w.strip("_")
    return bool(core) and (w.startswith("_") or "_" in core or re.search(r"[a-z0-9][A-Z]|[A-Z]{2}[a-z]", w) is not None)


def issue_mentions(text: str) -> list[dict]:
    """Identifier-shaped strings with their first position and rule."""
    found = {}

    def add(s, pos, how):
        for pre in ("self.", "cls."):
            if s.startswith(pre):
                s = s[len(pre):]
                # outside inline code, a bare name left by "self.x" must look like an identifier
                if "." not in s and how != "inline_code" and not _identifier_shaped(s):
                    return
        s = s.strip(".")
        if s and (s not in found or pos < found[s]["pos"]):
            found[s] = {"mention": s, "pos": pos, "rule": how}

    for m in _FRAME.finditer(text):
        add(f"frame:{m.group(1)}:{m.group(2)}:{m.group(3)}", m.start(), "traceback")
    for m in _INLINE_CODE.finditer(text):
        for w in _DOTTED.finditer(m.group(1)):
            add(w.group(0), m.start(1) + w.start(), "inline_code")
        for w in _IDENT.finditer(m.group(1)):
            add(w.group(0), m.start(1) + w.start(), "inline_code")
    for m in _DOTTED.finditer(text):
        add(m.group(0), m.start(), "dotted")
    for m in _IDENT.finditer(text):
        if _identifier_shaped(m.group(0)):
            add(m.group(0), m.start(), "identifier")
    return sorted(found.values(), key=lambda d: (d["pos"], d["mention"]))


class NodeIndex:
    """Lookup of graph nodes by trailing components, package and module path."""

    def __init__(self, nodes):
        self.nodes = {n["id"]: n for n in nodes}
        self.by_suffix = defaultdict(set)
        self.by_module_name = defaultdict(set)
        for nid, n in self.nodes.items():
            parts = nid.split(".")
            for k in range(1, len(parts) + 1):
                self.by_suffix[".".join(parts[-k:])].add(nid)
            if n.get("module"):
                self.by_module_name[(n["module"], parts[-1])].add(nid)

    def match_name(self, mention: str) -> set:
        hit = self.by_suffix.get(mention, set())
        if hit:
            return set(hit)
        parts = mention.split(".")
        if len(parts) >= 2:
            rest = ".".join(parts[1:])
            return {nid for nid in self.by_suffix.get(rest, ()) if nid.split(".")[0] == parts[0]}
        return set()

    def match_frame(self, path: str, line: int, func: str) -> set:
        p = path.replace("\\", "/")
        cands = set()
        for (mod, name), ids in self.by_module_name.items():
            if name != func:
                continue
            rel = mod.replace(".", "/")
            if p.endswith("/" + rel + ".py") or p == rel + ".py" or p.endswith("/" + rel + "/__init__.py"):
                cands |= ids
        if len(cands) > 1:
            inside = {c for c in cands if (self.nodes[c].get("lineno") or 0) <= line <= (self.nodes[c].get("end_lineno") or -1)}
            if len(inside) == 1:
                return inside
        return cands


def find_anchors(text: str, index: NodeIndex, degree, max_degree: int = MAX_ANCHOR_DEGREE) -> dict:
    """Anchors (unique node matches of degree <= max_degree) in order of first mention."""
    anchors, seen, ambiguous, too_connected = [], set(), [], []
    for m in issue_mentions(text):
        s = m["mention"]
        if s.startswith("frame:"):
            path, line, func = s[6:].rsplit(":", 2)
            hits = index.match_frame(path, int(line), func)
        else:
            hits = index.match_name(s)
        if len(hits) > 1:
            ambiguous.append(s)
            continue
        if not hits:
            continue
        (nid,) = hits
        if degree(nid) > max_degree:
            too_connected.append(nid)
            continue
        if nid not in seen:
            seen.add(nid)
            anchors.append({"node": nid, "mention": s, "rule": m["rule"], "pos": m["pos"]})
    return {"anchors": anchors, "ambiguous": ambiguous, "too_connected": sorted(set(too_connected))}


def hop_distance(sources, targets, neighbours, max_hops: int = 2):
    """Smallest number of undirected hops from any source to any target (None if > max_hops)."""
    targets = set(targets)
    dist = {s: 0 for s in sources}
    dq = deque(sources)
    while dq:
        x = dq.popleft()
        if x in targets:
            return dist[x]
        if dist[x] == max_hops:
            continue
        for y in sorted(neighbours(x)):
            if y not in dist:
                dist[y] = dist[x] + 1
                dq.append(y)
    return None


def stratum(anchor_nodes, gold, neighbours) -> str:
    d = hop_distance(list(anchor_nodes), gold, neighbours) if anchor_nodes and gold else None
    return {0: "S0", 1: "S1", 2: "S2"}.get(d, "S3")


def undirected_neighbours(edges):
    nb = defaultdict(set)
    for e in edges:
        s, t = e["source"], e["target"]
        if s != t:
            nb[s].add(t)
            nb[t].add(s)
    return nb

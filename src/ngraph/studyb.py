"""Study B tasks and prompts (pre-registration, section 4; fixed in the Study B addendum, prereg-v1.1).

A task record (`build_task`) holds identifiers only: gold functions, the BM25 pool with ranks, anchors,
stratum, the two candidate orders and the node and edge lists that the two graph-tool calls return on
the true and on the rewired graph. Prompts are rendered from the record and the task's text
(`render_task`) and are never stored; their SHA-256 values are, so that a run can check that it scores
exactly the frozen prompts.

Prompt (user turn), one per naming x graph x order:

    An issue was reported in a Python repository:

    <issue text, possibly cut>

    Candidate functions (each shown with up to its first 15 lines):

    A. <qualified name>
    ```python
    <code>
    ```
    ... (B to J)

    [graph conditions only:]
    Output of the repository's code-graph tools:
    get_code_subgraph(<the anchors and the ten candidates>) returned:
    {"status": "ok", "nodes": [...], "edges": [{"from": ..., "to": ..., "type": "calls"}, ...], ...}
    get_code_neighbors("<first anchor>") returned:          (anchored tasks only)
    {"status": "ok", "node": ..., "neighbors": [...], "count": N, "is_truncated": false}

    Question: Which one of these functions most likely has to be changed to resolve the issue?
    Answer with the letter of the correct option only.

Rules (each an addendum item):
* Tool outputs in the official JSON shapes (competition harness README, section 6.3), structure only
  (no source text). Subgraph: the induced subgraph on the anchors and the ten candidates (in that order,
  duplicates once), edges sorted by (from, to) of the real names, self-loops kept as in the graph.
  Neighbours: of the first anchor, sorted by real name, at most 50. Each list (nodes, edges,
  neighbours) is cut to whole items whose JSON is at most 5,000 characters, measured on the real
  names; `is_truncated` is then true and `count` is the number listed. The opaque prompt shows the
  same items, renamed. The rewired condition calls the same tools on the rewired graph.
* Candidates: qualified name, then the first 15 lines of the source from the first decorator,
  dedented; lines longer than 200 characters are cut at the last space or punctuation before 200 and
  end with " ...". Code is cut first and renamed after (renaming is token by token, so this equals
  cutting the renamed code at the same tokens).
* Length: every prompt of a task must fit TOKEN_BUDGET tokens (n_ctx 8,192 minus 256 for the chat
  template and the answer prefix). If the longest of the task's prompts does not fit, the issue is
  cut at the largest offset of the original text (at a line or space boundary) for which all fit, and
  the opaque text is cut at the mapped offset (rename.map_offset); " [...]" marks the cut. If the
  issue cut to 1,000 characters still does not fit, the candidates' line limit drops one line at a
  time (to at least 5), and then the issue is cut further. The cut and the line limit are recorded.
* Opaque naming renames the issue text (rename_issue), each qualified name and each candidate's code
  (rename_code) and each node name in the tool outputs (rename_code, name by name, so the JSON keys
  stay as they are).
"""

from __future__ import annotations

import hashlib
import json
import random
import re

from ngraph import localize as lz
from ngraph.items import stable_seed
from ngraph.runner import LETTERS10

STUDYB_VERSION = "0.1.0"
N_CTX = 8192
TEMPLATE_MARGIN = 256
TOKEN_BUDGET = N_CTX - TEMPLATE_MARGIN
CODE_LINES = 15
MIN_CODE_LINES = 5
MAX_LINE_CHARS = 200
TOOL_CHARS = 5000
MAX_NEIGHBORS = 50
ISSUE_FLOOR_CHARS = 1000
NAMINGS = ("real", "opaque")
GRAPHS = ("none", "true", "rewired")
ORDERS = (1, 2)
ORDER_SEED = 1
CUT_MARK = " [...]"
QUESTION = ("Question: Which one of these functions most likely has to be changed to resolve the issue?\n"
            "Answer with the letter of the correct option only.")


# ----------------------------------------------------------------------------- orders
def candidate_orders(task_id: str, pool: list) -> dict:
    """Order 1: seeded permutation (stable_seed(ORDER_SEED, task id, "order")); order 2: its reverse."""
    rng = random.Random(stable_seed(ORDER_SEED, task_id, "order"))
    o1 = list(pool)
    rng.shuffle(o1)
    return {1: o1, 2: list(reversed(o1))}


# ----------------------------------------------------------------------------- tool outputs
def _cap_list(items: list, limit: int = TOOL_CHARS) -> tuple[list, bool]:
    """Longest prefix of whole items whose JSON (json.dumps of the list) is at most `limit` chars."""
    out = []
    for x in items:
        if len(json.dumps(out + [x])) > limit:
            return out, True
        out.append(x)
    return out, False


def subgraph_call(nodes: list, edge_set: set) -> dict:
    """Induced subgraph on `nodes` (official get_code_subgraph shape, real names, before renaming)."""
    seen, order = set(), []
    for n in nodes:
        if n not in seen:
            seen.add(n)
            order.append(n)
    edges = sorted((s, t) for s, t in edge_set if s in seen and t in seen)
    kept_nodes, t1 = _cap_list(order)
    kept_edges, t2 = _cap_list([{"from": s, "to": t, "type": "calls"} for s, t in edges])
    return {"nodes": kept_nodes, "edges": [(e["from"], e["to"]) for e in kept_edges],
            "is_truncated": bool(t1 or t2), "n_nodes_full": len(order), "n_edges_full": len(edges)}


def neighbors_call(node: str, nb: dict) -> dict:
    allnb = sorted(nb.get(node, ()))
    head = allnb[:MAX_NEIGHBORS]
    kept, t = _cap_list(head)
    return {"node": node, "neighbors": kept, "is_truncated": bool(t or len(allnb) > MAX_NEIGHBORS),
            "n_full": len(allnb)}


def graph_context(anchors: list, pool: list, edges) -> dict:
    """Both tool calls on one graph (edges: iterable of (source, target, type)). `pool` must be in a
    rank-free order (build_task passes the order-1 candidate order, never the BM25 ranking)."""
    edge_set = {(s, t) for s, t, _ in edges}
    nb = {}
    for s, t in edge_set:
        if s != t:
            nb.setdefault(s, set()).add(t)
            nb.setdefault(t, set()).add(s)
    out = {"subgraph": subgraph_call(list(anchors) + list(pool), edge_set),
           "n_anchors": len(anchors), "n_candidates": len(pool)}
    if anchors:
        out["neighbors"] = neighbors_call(anchors[0], nb)
    return out


# the fixed words of the tool-output format (render_tool_output): JSON keys, the literal values "ok",
# "calls", true and false, and the two tool names. They are the same in every prompt of every repository,
# so the leak scan ignores them even when a repository defines a name such as node_count (pylint) (0.1.3)
TOOL_LINE_RE = re.compile(r'^(?:\{"status": "ok", "nodes?": .*|get_code_(?:subgraph|neighbors)\(.*\) returned:)$', re.M)
TOOL_FIXED_RE = re.compile(r'"(?:status|nodes|edges|from|to|type|node_count|edge_count|is_truncated|node|neighbors|count)": '
                           r'|(?<="status": )"ok"(?=, )|(?<="type": )"calls"(?=\})|(?<="is_truncated": )(?:true|false)(?=[,}])'
                           r'|^get_code_(?:subgraph|neighbors)(?=\()',
                           re.M)


def leak_text(prompt: str) -> str:
    """The prompt with the fixed words of the tool output blanked (same length), for the leak scan only."""
    out = list(prompt)
    for line in TOOL_LINE_RE.finditer(prompt):
        for m in TOOL_FIXED_RE.finditer(prompt, line.start(), line.end()):
            out[m.start():m.end()] = " " * (m.end() - m.start())
    return "".join(out)


def render_tool_output(ctx: dict, name) -> str:
    sg = ctx["subgraph"]
    sub = {"status": "ok", "nodes": [name(n) for n in sg["nodes"]],
           "edges": [{"from": name(s), "to": name(t), "type": "calls"} for s, t in sg["edges"]],
           "node_count": len(sg["nodes"]), "edge_count": len(sg["edges"]), "is_truncated": sg["is_truncated"]}
    n_c, n_a = ctx.get("n_candidates", 10), ctx.get("n_anchors", 0)
    what = (f"the {n_a} issue anchor{'s' if n_a != 1 else ''} and the {n_c} candidates" if n_a
            else f"the {n_c} candidates")
    lines = ["Tool output:", f"get_code_subgraph(<{what}>) returned:", json.dumps(sub)]
    if "neighbors" in ctx:
        nbc = ctx["neighbors"]
        res = {"status": "ok", "node": name(nbc["node"]), "neighbors": [name(n) for n in nbc["neighbors"]],
               "count": len(nbc["neighbors"]), "is_truncated": nbc["is_truncated"]}
        lines += [f"get_code_neighbors({json.dumps(name(nbc['node']))}) returned:", json.dumps(res)]
    return "\n".join(lines)


# ----------------------------------------------------------------------------- code display
_BREAK = re.compile(r"[\s,;:()\[\]{}.=+\-*/<>]")


def cut_line(line: str, limit: int = MAX_LINE_CHARS) -> str:
    if len(line) <= limit:
        return line
    k = max((m.start() for m in _BREAK.finditer(line, 0, limit)), default=-1)
    k = k if k > 0 else limit
    return line[:k].rstrip() + " ..."


def dedent_lines(lines: list) -> list:
    """Remove the first non-blank line's indentation (spaces and tabs) from every line that starts with it;
    a less-indented line (a multi-line string at column 0) is kept as it is and does not block the rest.
    Blank = only spaces and tabs. The same on every Python version (textwrap.dedent's idea of whitespace
    changed between 3.13 and 3.14)."""
    body = [x for x in lines if x.strip(" \t")]
    if not body:
        return ["" for _ in lines]
    pre = body[0][: len(body[0]) - len(body[0].lstrip(" \t"))]
    return [("" if not x.strip(" \t") else x[len(pre):] if x.startswith(pre) else x) for x in lines]


def display_code(source: str, n_lines: int = CODE_LINES) -> str:
    from ngraph.official import source_lines

    lines = dedent_lines(source_lines(source)[:n_lines])
    return "\n".join(cut_line(x) for x in lines)


def signature(source: str, name: str) -> str:
    """Compact signature: the function's name and parameter names, e.g. get(self, path, *, tags, **kw);
    the full def line may run past the line limit (decorators, long annotated parameters)."""
    import ast

    from ngraph.official import source_lines

    short = name.rsplit(".", 1)[-1]
    lines = source_lines(source)
    i = next((k for k, x in enumerate(lines) if x.lstrip(" \t").startswith(("def ", "async def "))), None)
    if i is None:
        return short + "(...)"
    ind = lines[i][: len(lines[i]) - len(lines[i].lstrip(" \t"))]
    fn = None
    # parse only the header of the first def (its own indentation removed), growing it line by line until
    # it parses with a stub body; the rest of the span (a merged getter/setter, an else branch) is ignored
    for j in range(i, min(len(lines), i + 60)):
        hdr = "\n".join(x[len(ind):] if x.startswith(ind) else x.lstrip(" \t") for x in lines[i:j + 1])
        for text in (hdr + "\n    pass", hdr):
            try:
                node = ast.parse(text).body[0]
            except (SyntaxError, ValueError, IndexError):
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn = node
                break
        if fn is not None:
            break
    if fn is None:
        return short + "(...)"
    a = fn.args
    parts = [x.arg for x in a.posonlyargs]
    if a.posonlyargs:
        parts.append("/")
    parts += [x.arg for x in a.args]
    if a.vararg:
        parts.append("*" + a.vararg.arg)
    elif a.kwonlyargs:
        parts.append("*")
    parts += [x.arg for x in a.kwonlyargs]
    if a.kwarg:
        parts.append("**" + a.kwarg.arg)
    return cut_line(f"{fn.name}({', '.join(parts)})")


# ----------------------------------------------------------------------------- task record
def build_task(task: dict, graph: dict, rewired_edges, index, lib_ids: list, set_name: str = "official") -> dict:
    """Identifiers-only record of one task. `graph` from official.load_graph (or the Lite equivalent);
    `index` a SnapshotIndex-like object (read, module_of, source, node); lib_ids the library functions."""
    tid = task["instance_id"]
    issue = normalise_issue(task["problem_statement"])
    node_ids = list(graph["nodes"])
    g = lz.gold_functions(task["patch"], index.read, index.module_of, node_ids)
    lib = set(lib_ids)
    gold = sorted(x for x in g["gold"] if x in lib)
    rec = {"task_id": tid, "set": set_name, "repo": task["repo"], "base_commit": task["base_commit"],
           "gold_all": g["gold"], "gold": gold, "gold_files": g["files"], "eligible": bool(gold),
           "n_library_functions": len(lib), "studyb_version": STUDYB_VERSION}
    if not gold:
        rec["excluded_reason"] = "no library function in the gold patch"
        return rec
    docs = {nid: nid + "\n" + index.source(nid) for nid in sorted(lib)}
    scores = lz.BM25(docs).scores(issue)
    pool = lz.candidate_pool(scores, gold)
    nb = {}
    for s, t, _ in graph["edges"]:
        if s != t:
            nb.setdefault(s, set()).add(t)
            nb.setdefault(t, set()).add(s)
    recs = []
    for nid in node_ids:
        r = index.node.get(nid)
        recs.append({"id": nid, **r} if r else {"id": nid})
    anchors = lz.find_anchors(issue, lz.NodeIndex(recs), lambda n: len(nb.get(n, ())))
    orders = candidate_orders(tid, pool["pool"])
    anchor_nodes = [a["node"] for a in anchors["anchors"]]
    rec.update({
        "pool": pool["pool"], "injected": pool["injected"], "gold_ranks": pool["gold_ranks"],
        "gold_in_pool": pool["gold_in_pool"],
        "bm25_pool_scores": {n: round(scores[n], 6) for n in pool["pool"]},
        "anchors": [{"node": a["node"], "rule": a["rule"]} for a in anchors["anchors"]],
        "n_ambiguous_mentions": len(anchors["ambiguous"]), "too_connected": anchors["too_connected"],
        "anchored": bool(anchor_nodes),
        "stratum": lz.stratum(anchor_nodes, gold, lambda n: nb.get(n, ())),
        "orders": orders,
        "context": {"true": graph_context(anchor_nodes, orders[1], graph["edges"]),
                    "rewired": graph_context(anchor_nodes, orders[1], rewired_edges)},
        # B5 (model-free scorer): candidates adjacent to any anchor in each graph (full graphs, no cut)
        "b5_anchor_neighbours": {"true": anchor_adjacent(anchor_nodes, pool["pool"], graph["edges"]),
                                 "rewired": anchor_adjacent(anchor_nodes, pool["pool"], rewired_edges)},
    })
    rec["correct_letters"] = {o: sorted(LETTERS10[i] for i, c in enumerate(rec["orders"][o]) if c in gold)
                              for o in ORDERS}
    return rec


def anchor_adjacent(anchors, pool, edges) -> list:
    """Pool candidates that share an edge (either direction) with at least one anchor."""
    a = set(anchors)
    adj = set()
    for s, t, _ in edges:
        if s != t:
            if s in a:
                adj.add(t)
            if t in a:
                adj.add(s)
    return [c for c in pool if c in adj]


# ----------------------------------------------------------------------------- rendering
_FENCE_LINE = re.compile(r"^[ \t]*(`{3,}|~{3,})", re.M)


def normalise_issue(text: str) -> str:
    """Line ends as \\n (the renamer's fence and traceback rules work line by line)."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def close_fence(prefix: str) -> str:
    """Text appended after a cut so that a code fence opened before the cut is closed."""
    fences = _FENCE_LINE.findall(prefix)
    return "\n" + fences[-1] if len(fences) % 2 == 1 else ""
def _assemble(issue: str, cands: list, tool: str | None, code_lines: int = CODE_LINES) -> str:
    parts = ["An issue was reported in a Python repository:", "", issue.strip(), "",
             f"Candidate functions (qualified name and signature, then up to the first {code_lines} lines of "
             "the source):", ""]
    for i, (qn, sig, code) in enumerate(cands):
        parts += [f"{LETTERS10[i]}. {qn}", f"Signature: {sig}", "```python", code, "```", ""]
    if tool:
        parts += [tool, ""]
    parts.append(QUESTION)
    return "\n".join(parts)


def prompt_keys(rec: dict) -> list:
    """(naming, graph, order) of every prompt of a task: 12 confirmatory ones, plus the opaque
    within-module prompts (exploratory) when the record has that context."""
    keys = [(n, g, o) for n in NAMINGS for g in GRAPHS for o in ORDERS]
    if "within_module" in (rec.get("context") or {}):
        keys += [("opaque", "within_module", o) for o in ORDERS]
    return keys


def render_fixed(rec: dict, task: dict, index, renamer, cut_at, code_lines: int, keys=None) -> dict:
    """{(naming, graph, order): text} with a given issue cut (None: no cut) and candidate line limit."""
    from ngraph.rename import map_offset

    issue = normalise_issue(task["problem_statement"])
    k = len(issue) if cut_at is None else cut_at
    cut = k < len(issue)
    tail = (CUT_MARK + close_fence(issue[:k])) if cut else ""
    keys = prompt_keys(rec) if keys is None else keys
    out, codes, names, issues = {}, {}, {}, {}
    for naming, graph, o in keys:
        if naming not in issues:
            if naming == "real":
                issues[naming] = issue[:k] + tail
                names[naming] = lambda x: x
            else:
                ren = renamer.rename_issue(issue)
                kk = map_offset(ren.spans, k) if cut else len(ren.text)
                issues[naming] = ren.text[:kk] + tail
                cache = {}

                def f(x, cache=cache):
                    if x not in cache:
                        cache[x] = renamer.rename_code(x).text
                    return cache[x]
                names[naming] = f
        name = names[naming]
        tool = None if graph == "none" else render_tool_output(rec["context"][graph], name)
        cands = []
        for qn in rec["orders"][o]:
            ck = (naming, qn)
            if ck not in codes:
                src = index.source(qn)
                code, sig = display_code(src, code_lines), signature(src, qn)
                if naming == "opaque":
                    code, sig = renamer.rename_code(code).text, renamer.rename_code(sig).text
                codes[ck] = (sig, code)
            cands.append((name(qn), *codes[ck]))
        out[(naming, graph, o)] = _assemble(issues[naming], cands, tool, code_lines)
    return out


def render_task(rec: dict, task: dict, index, renamer, count_tokens, budget: int = TOKEN_BUDGET) -> dict:
    """All prompts of an eligible task with the registered cut (module docstring), plus `meta`.
    count_tokens(text) -> number of tokens (the Gemma 4 tokenizer in real runs)."""
    issue = normalise_issue(task["problem_statement"])
    cuts = sorted({m.start() for m in re.finditer(r"[\n ]", issue)} | {len(issue)})
    conf_keys = [k for k in prompt_keys(rec) if k[1] in GRAPHS]

    def attempt(k, n_lines):
        p = render_fixed(rec, task, index, renamer, None if k >= len(issue) else k, n_lines, conf_keys)
        return p, max(count_tokens(t) for t in p.values())

    prompts, top = attempt(len(issue), CODE_LINES)
    meta = {"issue_chars": len(issue), "cut_at": None, "code_lines": CODE_LINES, "max_tokens": top}
    if top <= budget:
        return _with_extra(rec, task, index, renamer, count_tokens, budget, prompts, meta)

    def search(lo_cut: int, n_lines: int):
        """Largest boundary cut >= lo_cut (below the full length) for which every prompt fits, or None."""
        cand = [c for c in cuts if lo_cut <= c < len(issue)]
        lo, hi, best = 0, len(cand) - 1, None
        while lo <= hi:
            mid = (lo + hi) // 2
            p, t = attempt(cand[mid], n_lines)
            if t <= budget:
                best = (cand[mid], p, t)
                lo = mid + 1
            else:
                hi = mid - 1
        return best

    floor = max([c for c in cuts if c <= ISSUE_FLOOR_CHARS], default=0)
    n_lines = CODE_LINES
    best = search(floor, n_lines)
    while best is None and n_lines > MIN_CODE_LINES:
        n_lines -= 1
        p, t = attempt(len(issue), n_lines)
        if t <= budget:
            best = (len(issue), p, t)
            break
        best = search(floor, n_lines)
    if best is None:
        best = search(0, n_lines)
    if best is None:
        raise RuntimeError(f"{rec['task_id']}: no cut fits {budget} tokens")
    k, prompts, top = best
    meta.update({"cut_at": None if k >= len(issue) else k, "code_lines": n_lines, "max_tokens": top})
    return _with_extra(rec, task, index, renamer, count_tokens, budget, prompts, meta)


def _with_extra(rec, task, index, renamer, count_tokens, budget, prompts, meta) -> dict:
    """Adds the exploratory within-module prompts, rendered with the confirmatory cut and line limit
    (they never change the confirmatory prompts); records their length and whether they fit."""
    extra = [k for k in prompt_keys(rec) if k[1] not in GRAPHS]
    if extra:
        p = render_fixed(rec, task, index, renamer, meta["cut_at"], meta["code_lines"], extra)
        top = max(count_tokens(t) for t in p.values())
        meta = dict(meta, max_tokens_exploratory=top, exploratory_fits=top <= budget)
        prompts = {**prompts, **p}
    return {"prompts": prompts, "meta": meta}


def prompt_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def job_key(task_id: str, naming: str, graph: str, order: int) -> dict:
    """Run-file keys (runner RUN_KEY = item_id, version, perm)."""
    return {"item_id": task_id, "version": f"{naming}/{graph}", "perm": order}


# ----------------------------------------------------------------------------- build (official tasks)
def _rewire(edges, kind_of=None, seed: int = 1):
    """Rewired copy of an official edge list [(s, t, type)] (ngraph.rewire, 10 x |E| swaps, seed 1),
    with its invariant check. kind_of: node -> group (the within-module null passes the module)."""
    from ngraph import rewire as rw

    ed = [{"source": s, "target": t, "type": ty} for s, t, ty in edges]
    new, rep = rw.rewire_edges(ed, kind_of=kind_of, seed=seed)
    rep["invariants"] = rw.check_invariants(ed, new, kind_of)
    if kind_of is not None:
        rep["same_group_share"] = {"before": rw.same_group_share(ed, kind_of),
                                   "after": rw.same_group_share(new, kind_of)}
    return [(e["source"], e["target"], e.get("type", "calls")) for e in new], rep


def vocab_counter(vocab_path: str):
    """Token counter with the Gemma 4 tokenizer (vocab-only llama.cpp model; no weights needed)."""
    from ngraph.runner import LetterScorer

    sc = LetterScorer(vocab_path, n_ctx=N_CTX, vocab_only=True)
    return lambda text: len(sc.tokenize(text, special=False))


def merge_names(parts: list):
    """One ProjectNames for a repository: the union over its snapshots (one bijection per repository,
    pre-registration section 4). A name defined in any snapshot is defined; a name imported from
    outside the repository in any snapshot is third-party (so protected)."""
    from ngraph.rename import ProjectNames

    defined, third, packages, identity, errors = {}, set(), set(), set(), []
    for p in parts:
        for k, kinds in p.defined.items():
            defined.setdefault(k, set()).update(kinds)
        third |= set(p.third_party)
        packages |= set(p.packages)
        identity |= set(p.identity)
        errors += list(p.parse_errors)
    return ProjectNames({k: sorted(v) for k, v in sorted(defined.items())}, third, sorted(packages),
                        sorted(identity), [], errors)


class OfficialSource:
    """The competition data folder, read lazily: graphs (with their rewired copies, cached per base
    commit) and, per task, the snapshot's Python files in a temporary folder (`task_context`)."""

    def __init__(self, data_dir: str):
        import os

        from ngraph import official as of

        self.of = of
        self.data_dir = data_dir
        self.tasks = {t["instance_id"]: t for t in of.load_tasks(os.path.join(data_dir, "tasks.jsonl"))}
        self.graphs, self.reports = {}, {}

    def graph(self, gname: str):
        import os

        if gname not in self.graphs:
            g = self.of.load_graph(os.path.join(self.data_dir, "graphs", gname + ".json"))
            rew, rep = _rewire(g["edges"])
            self.graphs[gname] = (g, rew)
            self.reports[gname] = {"stats": g["stats"], "rewired": rep}
        return self.graphs[gname]

    def within_module(self, gname: str, index):
        key = gname + "#within_module"
        if key not in self.graphs:
            g, _ = self.graph(gname)
            mods = set(index.module.values())

            def module_of_node(n):
                if n in index.node:
                    return index.node[n]["module"]
                parts = n.split(".")
                for i in range(len(parts) - 1, 0, -1):
                    if ".".join(parts[:i]) in mods:
                        return ".".join(parts[:i])
                return n.rsplit(".", 1)[0]
            mod = {n: module_of_node(n) for n in g["nodes"]}
            wm, wrep = _rewire(g["edges"], kind_of=mod.get)
            self.graphs[key] = (wm, None)
            self.reports[gname]["within_module"] = {k: wrep[k] for k in (
                "engine", "nswap", "swaps_done", "completed", "edge_overlap", "invariants", "same_group_share")}
        return self.graphs[key][0]

    def _snapshot_names(self, tid: str):
        import os
        import tempfile

        from ngraph import rename as rn

        of, t = self.of, self.tasks[tid]
        with tempfile.TemporaryDirectory() as tmp:
            files, _ = of.read_snapshot_py(os.path.join(self.data_dir, "snapshots", tid + ".tgz"))
            root = os.path.join(tmp, "tree")
            of.write_tree(files, root)
            return rn.collect_names(root, repo=of.short_repo(t), org=t["repo"].split("/")[0])

    def repo_names(self, repo: str):
        """ProjectNames of a repository: the union over the snapshots of all its tasks (cached)."""
        if not hasattr(self, "_names"):
            self._names = {}
        if repo not in self._names:
            tids = sorted(i for i, t in self.tasks.items() if t["repo"] == repo)
            self._names[repo] = merge_names([self._snapshot_names(i) for i in tids])
        return self._names[repo]

    def task_context(self, tid: str):
        """Context manager yielding a dict: task, graph, rewired, index, lib_ids, renamer and file info."""
        import contextlib
        import os
        import tempfile

        from ngraph import rename as rn

        of = self.of
        t = self.tasks[tid]

        @contextlib.contextmanager
        def ctx():
            gname = of.graph_name(t)
            g, rew = self.graph(gname)
            with tempfile.TemporaryDirectory() as tmp:
                files, skipped = of.read_snapshot_py(os.path.join(self.data_dir, "snapshots", tid + ".tgz"))
                root = os.path.join(tmp, "tree")
                of.write_tree(files, root)
                index = of.SnapshotIndex(root, g["nodes"])
                lib_files, finfo = of.library_files(root)
                names = self.repo_names(t["repo"])
                yield {"task": t, "gname": gname, "graph": g, "rewired": rew, "index": index,
                       "lib_ids": of.library_functions(index, lib_files), "finfo": finfo, "skipped": skipped,
                       "names": names, "renamer": lambda: self.renamer(t["repo"])}
        return ctx()

    def renamer(self, repo: str):
        from ngraph import rename as rn

        if not hasattr(self, "_renamers"):
            self._renamers = {}
        if repo not in self._renamers:
            self._renamers[repo] = rn.OpaqueRenamer(self.repo_names(repo), seed=1)
        return self._renamers[repo]


def build_records(src, set_name: str, count, ids=None, log=print) -> dict:
    """Task records, prompt hashes and graph reports (identifiers only) for every task of a source
    (OfficialSource or lite.LiteSource)."""
    records, maps = [], {}
    for tid in (sorted(src.tasks) if not ids else sorted(set(ids))):
        with src.task_context(tid) as c:
            t, index = c["task"], c["index"]
            rec = build_task(t, c["graph"], c["rewired"], index, c["lib_ids"], set_name=set_name)
            rec["role"] = c.get("role", "confirmatory")
            rec["graph"] = c["gname"]
            rec["index"] = index.stats(c["graph"]["nodes"])
            rec["library_groups"] = c["finfo"].get("kept_groups")
            rec["snapshot_skipped"] = c["skipped"]
            if rec["eligible"]:
                renamer = c["renamer"]()
                anchors = [a["node"] for a in rec["anchors"]]
                # within-module null (exploratory): swaps only between edges joining the same module pair
                rec["context"]["within_module"] = graph_context(anchors, rec["orders"][1],
                                                                src.within_module(c["gname"], index))
                rendered = render_task(rec, t, index, renamer, count)
                prompts = rendered["prompts"]
                rec["render"] = rendered["meta"]
                rec["prompt_sha256"] = {f"{n}/{gr}/{o}": prompt_sha(x) for (n, gr, o), x in sorted(prompts.items())}
                leaks, frame = {}, {}
                for (n, gr, o), x in prompts.items():
                    if n == "opaque":
                        sc = renamer.leak_scan(leak_text(x))
                        if not sc["ok"]:
                            leaks[f"{n}/{gr}/{o}"] = sc["hard"]
                        if sc.get("frame"):
                            frame[f"{n}/{gr}/{o}"] = sc["frame"]
                rec["hard_leaks"] = leaks
                rec["frame_names_kept"] = frame  # renamable names left in interpreter-made frame file names (0.1.3)
                rec["share_changed_issue"] = round(renamer.rename_issue(normalise_issue(t["problem_statement"])).share_changed, 4)
                names = c["names"]
                rec["renamer"] = {"names_renamed": len(renamer.map), "packages": names.packages,
                                  "identity": names.identity, "parse_errors": len(names.parse_errors)}
                exp = renamer.export()
                rec["rename_map_sha256"] = prompt_sha(json.dumps(exp, sort_keys=True))
                maps[t["repo"]] = exp
        records.append(rec)
        log(f"{tid}: eligible={rec['eligible']} gold={len(rec['gold'])} "
            f"injected={rec.get('injected')} anchored={rec.get('anchored')} stratum={rec.get('stratum')} "
            f"tokens={(rec.get('render') or {}).get('max_tokens')} cut={(rec.get('render') or {}).get('cut_at')} "
            f"leaks={len(rec.get('hard_leaks') or {})}")
    return {"records": records, "graph_reports": src.reports, "rename_maps": maps}


def summarise(records: list) -> dict:
    from collections import Counter

    el = [r for r in records if r["eligible"] and r.get("role", "confirmatory") == "confirmatory"]
    n = len(el)
    return {
        "tasks": len(records), "eligible": n, "roles": dict(Counter(r.get("role", "confirmatory") for r in records)),
        "eligible_tune": sum(bool(r["eligible"]) for r in records if r.get("role") == "tune"),
        "by_repo": dict(Counter(r["repo"] for r in el)),
        "injected": sum(r["injected"] for r in el),
        "anchored": sum(r["anchored"] for r in el),
        "anchored_share": (sum(r["anchored"] for r in el) / n) if n else None,
        "strata": dict(sorted(Counter(r["stratum"] for r in el).items())),
        "cut": sum((r.get("render") or {}).get("cut_at") is not None for r in el),
        "code_lines_reduced": sum((r.get("render") or {}).get("code_lines", CODE_LINES) < CODE_LINES for r in el),
        "tasks_with_hard_leaks": sum(bool(r.get("hard_leaks")) for r in el),
        "max_tokens": max(((r.get("render") or {}).get("max_tokens") or 0) for r in el) if el else None,
        "excluded": dict(Counter(r.get("excluded_reason") for r in records if not r["eligible"])),
    }


# ----------------------------------------------------------------------------- MC3
def mc3(src, per_repo: int = 1) -> dict:
    """MC3 (pre-registration, section 5): our extractor's edges against the official graph, on the
    snapshot of the latest base commit (by task created_at) of each competition repository. Compared on
    unordered pairs of library functions present in both node sets (the official graphs also hold
    classes, tests and class-to-method edges, which ours do not)."""
    import os
    import tempfile

    from ngraph import extract as ex

    of = src.of
    out = {}
    for repo in sorted({t["repo"] for t in src.tasks.values()}):
        tids = sorted((t["created_at"], i) for i, t in src.tasks.items() if t["repo"] == repo)[-per_repo:]
        for _, tid in tids:
            t = src.tasks[tid]
            g, _ = src.graph(of.graph_name(t))
            with tempfile.TemporaryDirectory() as tmp:
                files, _ = of.read_snapshot_py(os.path.join(src.data_dir, "snapshots", tid + ".tgz"))
                root = os.path.join(tmp, "tree")
                of.write_tree(files, root)
                index = of.SnapshotIndex(root, g["nodes"])
                lib = set(of.library_functions(index, of.library_files(root)[0]))
                sel, info = ex.select_files(root)
                mine = ex.extract(root, files=sel, file_info=info)
            ours_nodes = {n["id"] for n in mine["nodes"]}
            both = lib & ours_nodes
            und = lambda a, b: (a, b) if a <= b else (b, a)  # noqa: E731
            off = {und(a, b) for a, b, _ in g["edges"] if a != b and a in both and b in both}
            ours = {und(e["source"], e["target"]) for e in mine["links"] if e["source"] in both and e["target"] in both}
            inter = off & ours
            out[tid] = {"repo": repo, "graph": of.graph_name(t), "official_library_functions": len(lib),
                        "our_nodes": len(ours_nodes), "common_nodes": len(both), "official_pairs": len(off),
                        "our_pairs": len(ours), "common_pairs": len(inter),
                        "ours_in_official": len(inter) / len(ours) if ours else None,
                        "official_in_ours": len(inter) / len(off) if off else None}
    return out


# ----------------------------------------------------------------------------- runs
CELLS = {
    "confirmatory": [(n, g) for n in NAMINGS for g in GRAPHS],
    "within_module": [("opaque", "within_module")],
}


def load_task_file(path: str) -> dict:
    with open(path) as fh:
        d = json.load(fh)
    for r in d["tasks"]:
        if "orders" in r:
            r["orders"] = {int(k): v for k, v in r["orders"].items()}
        if "correct_letters" in r:
            r["correct_letters"] = {int(k): v for k, v in r["correct_letters"].items()}
    return d


def renaming_env() -> dict:
    """The Python version and a fingerprint of the names the renamer never touches (keywords, builtins,
    standard-library module names; they come from the running Python), recorded at build and compared at
    run so that a run under another Python stops with a clear message (the prompt hashes would catch it
    too)."""
    import hashlib
    import sys

    from ngraph import rename as rn

    names = "\n".join(sorted(rn.builtin_protected()))
    return {"python": sys.version.split()[0], "protected_names_sha256": hashlib.sha256(names.encode()).hexdigest()}


RESUME_KEYS = ("study", "tasks_sha256", "set", "cells", "roles")


def check_resume(out_path: str, header: dict) -> None:
    """Refuse to extend a run file begun for other tasks, another set, other cells or other roles (the
    runner itself compares the model, settings, package, perms, repos, versions and n_jobs)."""
    import os

    from ngraph import runner as rr

    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        return
    old = rr._read_header(out_path) or {}
    diff = [k for k in RESUME_KEYS if old.get(k) != header.get(k)]
    if diff:
        raise SystemExit(f"{out_path} was begun with " + "; ".join(f"{k}={old.get(k)!r}" for k in diff)
                         + "; now " + "; ".join(f"{k}={header.get(k)!r}" for k in diff) + ": start a new file (another --out)")


def study_b_jobs(source, records: list, cells, log=print) -> list:
    """Jobs in a fixed order (task id, naming, graph, order), each prompt rebuilt from the data and
    checked against its frozen SHA-256 (a mismatch stops the run before anything is scored)."""
    jobs, bad = [], []
    for rec in sorted(records, key=lambda r: r["task_id"]):
        keys = [(n, g, o) for n, g in cells for o in ORDERS]
        keys = [k for k in keys if f"{k[0]}/{k[1]}/{k[2]}" in rec["prompt_sha256"]]
        with source.task_context(rec["task_id"]) as c:
            prompts = render_fixed(rec, c["task"], c["index"], c["renamer"](), rec["render"]["cut_at"],
                                   rec["render"]["code_lines"], keys)
        for (n, g, o), text in prompts.items():
            key = f"{n}/{g}/{o}"
            if prompt_sha(text) != rec["prompt_sha256"][key]:
                bad.append(f"{rec['task_id']} {key}")
                continue
            jobs.append({**job_key(rec["task_id"], n, g, o), "set": rec["set"], "repo": rec["repo"],
                         "naming": n, "graph": g, "order": o, "anchored": rec["anchored"],
                         "stratum": rec["stratum"], "injected": rec["injected"],
                         "role": rec.get("role", "confirmatory"),
                         "correct_letters": rec["correct_letters"][o], "text": text})
        log(f"{rec['task_id']}: {len(keys)} prompts rebuilt")
    if bad:
        raise SystemExit(f"{len(bad)} prompts differ from the frozen SHA-256 (first: {bad[:5]}); nothing was scored")
    return jobs


def run_main(a) -> int:
    import hashlib
    import os
    import platform
    import sys
    import time

    from ngraph import runner as rr

    with open(a.tasks, "rb") as fh:
        tasks_sha = hashlib.sha256(fh.read()).hexdigest()
    d = load_task_file(a.tasks)
    env = renaming_env()
    built = {k: (d.get("params") or {}).get(k) for k in env}
    if built["protected_names_sha256"] is None:
        raise SystemExit(f"{a.tasks} records no protected-names fingerprint (params.protected_names_sha256): it was "
                         "built before this check; rebuild it with `build`")
    if built["protected_names_sha256"] != env["protected_names_sha256"]:
        raise SystemExit(f"{a.tasks} was built under Python {built['python']} with another set of protected names "
                         f"(sha256 {built['protected_names_sha256']}); this is Python {env['python']} "
                         f"({env['protected_names_sha256']}): run under the Python of the build")
    roles = set(a.roles.split(","))
    present = {r.get("role", "confirmatory") for r in d["tasks"]}
    if roles - present:
        raise SystemExit(f"--roles {sorted(roles - present)} not in {a.tasks} (roles there: {sorted(present)})")
    if (d.get("params") or {}).get("set") not in (None, a.set):
        raise SystemExit(f"{a.tasks} was built for --set {d['params']['set']}, not {a.set}")
    recs = [r for r in d["tasks"] if r.get("eligible") and r.get("role", "confirmatory") in roles]
    if a.only:
        recs = [r for r in recs if r["task_id"] in set(a.only)]
    if not recs:
        raise SystemExit("no eligible tasks selected")
    cells = [c for name in a.cells.split(",") for c in CELLS[name]]
    tag = a.tag.upper()
    tb = rr.thought_mode_for(tag, a.thought_block)
    if a.prefix_from:
        rr.read_smoke(a.prefix_from, tag)
    prefix = None if a.prefix_from else rr.answer_prefix_for(tag, a.answer_prefix, required=True)
    model_gguf = rr.gguf_info(a.model)
    pkg = rr.package_state(None)
    if a.prefix_from:
        groups, man_roles = rr._load_manifest(a.manifest)
        pilot = None if man_roles is None else [k for k, v in man_roles.items() if v == "pilot"]
        prefix, prefix_source = rr.prefix_from_smoke(a.prefix_from, tag, model_gguf.get("sha256"), tb,
                                                     rr.package_state(a.items_dir), pilot)
    else:
        prefix_source = {"rule": "ANSWER_PREFIX" if a.answer_prefix is None else "given (a deviation)"}
    source = make_source(a)
    jobs = study_b_jobs(source, recs, cells, log=lambda s: print(s, file=sys.stderr, flush=True))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    scorer = rr.LetterScorer(a.model, n_ctx=a.n_ctx, n_batch=a.n_batch, n_gpu_layers=a.n_gpu_layers,
                             flash_attn=a.flash_attn, thought_block=tb, answer_prefix=prefix)
    header = {"study": "B", "model_tag": tag, "model_file": os.path.basename(a.model), "settings": scorer.settings,
              "answer_prefix_source": prefix_source, "model_gguf": model_gguf, "model_n_params": scorer.n_params,
              "package": pkg, "tasks_file": os.path.basename(a.tasks), "tasks_sha256": tasks_sha,
              "perms": list(ORDERS), "versions": [f"{n}/{g}" for n, g in cells], "cells": a.cells,
              "roles": ",".join(sorted(roles)), "set": a.set, "renaming_env": env, "letter_ids": scorer.letter_ids(LETTERS10),
              "repos": sorted({r["repo"] for r in recs}), "n_tasks": len(recs),
              "platform": platform.platform(), "python": sys.version.split()[0], "n_jobs": len(jobs),
              "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    check_resume(a.out, header)
    print(json.dumps(rr.run_jobs(scorer, jobs, a.out, tag, header, letters=LETTERS10)))
    if a.repeat:
        print(json.dumps(repeat_check(scorer, jobs, a.out, a.repeat)))
    return 0


def repeat_check(scorer, jobs: list, run_path: str, n: int, seed: int = 0) -> dict:
    """Determinism (pre-registration, section 5): re-score n prompts drawn with `seed` and compare the
    arg-max letter and the largest letter-logit difference with the run file. Writes <run>.repeat.json."""
    from ngraph import runner as rr

    rows, _ = rr.load_results(run_path)
    by_key = {tuple(r[k] for k in rr.RUN_KEY): r for r in rows if "error" not in r}
    scored = [j for j in jobs if tuple(j[k] for k in rr.RUN_KEY) in by_key]
    missing = min(n, len(jobs)) - min(n, len(scored))  # fewer scored prompts than asked for
    pick = random.Random(seed).sample(scored, min(n, len(scored)))
    agree, diffs = 0, []
    for j in pick:
        r = by_key[tuple(j[k] for k in rr.RUN_KEY)]
        b = scorer.score(j["text"], LETTERS10)
        agree += b["pred_letter"] == r["pred_letter"]
        diffs.append(max(abs(b[f"logit_{L}"] - r[f"logit_{L}"]) for L in LETTERS10))
    k = len(diffs)
    out = {"n": k, "missing": missing, "seed": seed, "argmax_agreement": agree / k if k else None,
           "max_abs_logit_diff": max(diffs) if diffs else None,
           "passes": bool(k and missing == 0 and agree / k >= 0.99)}
    with open(run_path + ".repeat.json", "w") as fh:
        json.dump(out, fh, indent=1)
    return out


def make_source(args):
    if args.set == "official":
        if not args.data:
            raise SystemExit("--set official needs --data")
        return OfficialSource(args.data)
    from ngraph.lite import LiteSource

    if not (args.lite_test and args.repos_dir):
        raise SystemExit("--set lite needs --lite-test and --repos-dir (and --lite-dev for the tuning tasks)")
    return LiteSource(args.lite_test, args.repos_dir, args.lite_dev)


def main(argv=None) -> int:
    import argparse
    import os
    import sys

    ap = argparse.ArgumentParser(description="Build the Study B task files (identifiers only).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="build the frozen Study B task files of one set")
    b.add_argument("--set", required=True, choices=("official", "lite"))
    b.add_argument("--data", help="official: the unzipped competition data folder")
    b.add_argument("--lite-test", help="lite: SWE-bench Lite test split (JSON Lines)")
    b.add_argument("--lite-dev", help="lite: SWE-bench Lite dev split (JSON Lines; tuning tasks)")
    b.add_argument("--repos-dir", help="lite: folder of clones named <owner>__<name>")
    b.add_argument("--vocab", required=True, help="Gemma 4 vocab-only GGUF (third_party/llama.cpp)")
    b.add_argument("--only", nargs="*")
    b.add_argument("--out", required=True)
    m = sub.add_parser("mc3", help="manipulation check MC3: our extractor against the official graphs")
    m.add_argument("--data", required=True)
    m.add_argument("--out", required=True)
    r = sub.add_parser("run", help="score the Study B prompts of one model (resumable)")
    r.add_argument("--tasks", required=True, help="the frozen tasks.json")
    r.add_argument("--set", required=True, choices=("official", "lite"))
    r.add_argument("--data", help="official: the unzipped competition data folder")
    r.add_argument("--lite-test")
    r.add_argument("--lite-dev")
    r.add_argument("--repos-dir")
    r.add_argument("--model", required=True)
    r.add_argument("--tag", required=True)
    r.add_argument("--cells", default="confirmatory", help="confirmatory, within_module, or both (comma)")
    r.add_argument("--roles", default="confirmatory", help="task roles to run, comma-separated (confirmatory; tune = the Lite dev split: B5's lambda and the Study B pilot)")
    r.add_argument("--only", nargs="*", help="task ids (a partial run; for tests and pilots)")
    r.add_argument("--thought-block", default="auto", choices=("auto", "template", "on", "off"))
    r.add_argument("--n-ctx", type=int, default=N_CTX)
    r.add_argument("--n-batch", type=int, default=512)
    r.add_argument("--n-gpu-layers", type=int, default=-1)
    r.add_argument("--flash-attn", action="store_true")
    pg = r.add_mutually_exclusive_group()
    pg.add_argument("--answer-prefix", default=None)
    pg.add_argument("--prefix-from", metavar="SMOKE_JSON",
                    help="the model's GNG-1 smoke file (as for study-a; needs --items-dir and --manifest)")
    r.add_argument("--items-dir", default="data/items")
    r.add_argument("--manifest", default="data/repos_manifest.json")
    r.add_argument("--repeat", type=int, default=100, help="prompts re-scored for the determinism check (0: none)")
    r.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "run":
        return run_main(args)
    if args.cmd == "mc3":
        res = mc3(OfficialSource(args.data))
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as fh:
            json.dump(res, fh, indent=1, sort_keys=True)
        print(json.dumps(res, indent=1))
        return 0
    if args.cmd == "build":
        src = make_source(args)
        res = build_records(src, args.set, vocab_counter(args.vocab), args.only,
                            log=lambda x: print(x, file=sys.stderr, flush=True))
        os.makedirs(args.out, exist_ok=True)
        summ = summarise(res["records"])
        params = {"studyb_version": STUDYB_VERSION, "set": args.set, "n_ctx": N_CTX, "token_budget": TOKEN_BUDGET,
                  "code_lines": CODE_LINES, "max_line_chars": MAX_LINE_CHARS, "tool_chars": TOOL_CHARS,
                  "max_neighbors": MAX_NEIGHBORS, "order_seed": ORDER_SEED, "rename_seed": 1, "rewire_seed": 1,
                  "pool_k": lz.POOL_K, "bm25": [lz.K1, lz.B], "max_anchor_degree": lz.MAX_ANCHOR_DEGREE,
                  **renaming_env()}
        with open(os.path.join(args.out, "tasks.json"), "w") as fh:
            json.dump({"params": params, "summary": summ, "tasks": res["records"]}, fh, indent=1, sort_keys=True)
        with open(os.path.join(args.out, "graphs_report.json"), "w") as fh:
            json.dump(res["graph_reports"], fh, indent=1, sort_keys=True)
        import gzip
        with gzip.GzipFile(os.path.join(args.out, "rename_maps.json.gz"), "wb", mtime=0) as fh:
            fh.write(json.dumps(res["rename_maps"], sort_keys=True).encode())
        print(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

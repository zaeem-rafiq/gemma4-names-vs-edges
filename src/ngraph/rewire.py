"""Degree-preserving rewiring of a repository call graph (Study B, "rewired" condition).

Rules (pre-registration items; pre-registration, section 4), checked against the networkx 3.7 source:

* A mirrored graph (every edge u->v has a reverse v->u of the same type) is rewired as its
  undirected projection and mirrored again afterwards, so its reciprocity stays 1.0. Any other
  graph is rewired as a directed graph, which keeps every in-degree and out-degree.
* The number of swaps is ``factor`` x |E| (default 10), where |E| counts the non-loop edges of
  the graph that is swapped: unordered pairs for a mirrored graph, directed edges otherwise.
  The number of attempts is capped at ``max_tries_factor`` x |E| (default 100).
* Swaps stay inside a swap class: edges of one type whose endpoint kinds match (the unordered
  kind pair for a mirrored graph, the ordered pair for a directed one). Every node then keeps its
  degree within each edge type and its number of neighbours of each kind.
* A mirrored graph with one swap class whose two endpoint kinds are equal (always the case when
  nodes carry no kind and edges one type) is swapped by networkx's ``double_edge_swap`` on the
  undirected projection. Every other graph, and every directed graph, is swapped by our own loop
  with the same acceptance rule (no self-loops, no parallel edges); the report says which engine ran.
* Directed graphs use two-edge swaps (u->v and x->y become u->y and x->v), which keep every
  in-degree and out-degree. networkx's ``directed_edge_swap`` (three-edge swaps) is not the default
  since version 0.2.0: on the 44 Study A call graphs (extractor 0.3.0; directed, seed 1, factor 10,
  7 Nov 2026) it hit the attempt cap on 12 graphs and left a median 43.8% of edges in place (13 and
  47.6% on the extractor 0.2.0 graphs), while the two-edge loop completed on all 44 and left a
  median 2.4% (max 8.0%). ``engine="networkx"`` still runs it
  for comparison. Two-edge swaps cannot reverse a directed triangle, so they do not reach every
  graph with the same degrees.
* Self-loops stay where they are. Edge attributes that are constant within a swap class are
  copied to the rewired edges; attributes that vary within a class are dropped and listed in the
  report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from collections import Counter, defaultdict

import networkx as nx

REWIRE_VERSION = "0.2.0"  # 0.2.0: directed graphs use the two-edge loop by default
_MISSING = object()


def _jkey(x) -> str:
    return json.dumps(x, sort_keys=True)


def reciprocity(pairs) -> float | None:
    """Share of directed non-loop edges whose reverse edge is also present (None if no edges)."""
    s = set(map(tuple, pairs))
    nl = [(a, b) for a, b in s if a != b]
    if not nl:
        return None
    return sum((b, a) in s for a, b in nl) / len(nl)


def is_mirrored(edges, type_key: str | None = "type") -> bool:
    """True if every non-loop edge has a reverse edge of the same type."""
    typed = {(e["source"], e["target"]): (e.get(type_key) if type_key else None) for e in edges}
    return all(a == b or typed.get((b, a), _MISSING) == t for (a, b), t in typed.items())


def _check_simple(edges) -> None:
    seen = set()
    for e in edges:
        p = (e["source"], e["target"])
        if p in seen:
            raise ValueError(f"duplicate edge {p}: rewiring assumes a simple graph")
        seen.add(p)


def _attrs(e) -> dict:
    return {k: v for k, v in e.items() if k not in ("source", "target")}


def _profile(edges, kind_of, type_key):
    out_deg, in_deg, out_mix, in_mix, types = Counter(), Counter(), Counter(), Counter(), Counter()
    for e in edges:
        s, t = e["source"], e["target"]
        ty = _jkey(e.get(type_key)) if type_key else "null"
        out_deg[(s, ty)] += 1
        in_deg[(t, ty)] += 1
        out_mix[(s, ty, kind_of(t))] += 1
        in_mix[(t, ty, kind_of(s))] += 1
        types[ty] += 1
    return out_deg, in_deg, out_mix, in_mix, types


def check_invariants(before, after, kind_of=None, type_key: str | None = "type") -> dict:
    """Compare a graph's edge list with its rewired copy.

    Per node and edge type: out-degree, in-degree and the kinds of out- and in-neighbours.
    Globally: edge-type counts, self-loops, parallel edges and reciprocity.
    """
    kind_of = kind_of or (lambda n: "")
    ob, ib, omb, imb, tb = _profile(before, kind_of, type_key)
    oa, ia, oma, ima, ta = _profile(after, kind_of, type_key)
    pb = [(e["source"], e["target"]) for e in before]
    pa = [(e["source"], e["target"]) for e in after]
    loops_b = sorted(p for p in pb if p[0] == p[1])
    loops_a = sorted(p for p in pa if p[0] == p[1])
    rb, ra = reciprocity(pb), reciprocity(pa)
    out = {
        "degrees_equal": ob == oa and ib == ia,
        "edge_type_counts_equal": tb == ta,
        "neighbour_kind_mix_equal": omb == oma and imb == ima,
        "self_loops_unchanged": loops_b == loops_a,
        "no_parallel_edges": len(set(pa)) == len(pa),
        "reciprocity_before": rb,
        "reciprocity_after": ra,
    }
    out["all_ok"] = all(out[k] for k in ("degrees_equal", "edge_type_counts_equal",
                                         "neighbour_kind_mix_equal", "self_loops_unchanged",
                                         "no_parallel_edges"))
    return out


def same_group_share(edges, group_of) -> float | None:
    """Share of non-loop edges whose two endpoints are in the same group (e.g. module)."""
    nl = [(e["source"], e["target"]) for e in edges if e["source"] != e["target"]]
    if not nl:
        return None
    return sum(group_of(a) is not None and group_of(a) == group_of(b) for a, b in nl) / len(nl)


def _swap_loop(pairs, cls, same_kind, nswap, max_tries, rng, undirected):
    """Constrained swaps in place. pairs: list of [u, v]; for a mixed-kind class in undirected
    mode each pair is oriented (kind a, kind b) with a < b, and swaps keep that orientation.
    Returns (swaps per class, tries)."""
    key = (lambda a, b: (a, b) if a <= b else (b, a)) if undirected else (lambda a, b: (a, b))
    present = {key(u, v) for u, v in pairs}
    buckets = defaultdict(list)
    for i, c in enumerate(cls):
        buckets[c].append(i)
    pool = [i for i, c in enumerate(cls) if len(buckets[c]) >= 2]
    swaps = Counter()
    done = tries = 0
    if not pool:
        return swaps, 0
    while done < nswap and tries < max_tries:
        tries += 1
        i = pool[rng.randrange(len(pool))]
        c = cls[i]
        b = buckets[c]
        j = b[rng.randrange(len(b))]
        if i == j:
            continue
        u, v = pairs[i]
        x, y = pairs[j]
        if undirected and same_kind[c] and rng.random() < 0.5:
            x, y = y, x
        if u == y or x == v:
            continue
        k1, k2 = key(u, y), key(x, v)
        if k1 in present or k2 in present:
            continue
        present.discard(key(u, v))
        present.discard(key(x, y))
        present.add(k1)
        present.add(k2)
        pairs[i] = [u, y]
        pairs[j] = [x, v]
        swaps[c] += 1
        done += 1
    return swaps, tries


def _nx_swap(pairs, nswap, max_tries, seed, undirected):
    """networkx swaps on a graph built in sorted order (so a seed gives one result)."""
    G = nx.Graph() if undirected else nx.DiGraph()
    G.add_nodes_from(sorted({n for p in pairs for n in p}))
    G.add_edges_from(sorted(tuple(p) for p in pairs))
    fn = nx.double_edge_swap if undirected else nx.directed_edge_swap
    error = None
    try:
        fn(G, nswap=nswap, max_tries=max_tries, seed=random.Random(seed))
    except (nx.NetworkXAlgorithmError, nx.NetworkXError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    return [list(e) for e in G.edges()], error


def rewire_edges(edges, kind_of=None, type_key: str | None = "type", mode: str = "auto",
                 factor: float = 10, max_tries_factor: float = 100, seed: int = 1,
                 engine: str = "auto"):
    """Rewire a list of edge dicts ({"source", "target", ...attrs}).

    kind_of: node id -> kind label (None: all nodes one kind). mode: auto | mirrored | directed.
    engine: auto | networkx | constrained. Returns (new edge list, report).
    """
    if mode not in ("auto", "mirrored", "directed"):
        raise ValueError(f"unknown mode {mode!r}")
    if engine not in ("auto", "networkx", "constrained"):
        raise ValueError(f"unknown engine {engine!r}")
    _check_simple(edges)
    kind_of = kind_of or (lambda n: "")
    mirrored = is_mirrored(edges, type_key)
    if mode == "mirrored" and not mirrored:
        raise ValueError("mode='mirrored' but the graph is not fully mirrored")
    undirected = mirrored if mode == "auto" else mode == "mirrored"

    loops = [e for e in edges if e["source"] == e["target"]]
    nonloop = [e for e in edges if e["source"] != e["target"]]
    # one record per swapped edge: undirected pairs for a mirrored graph
    units = {}
    for e in nonloop:
        a, b = e["source"], e["target"]
        ty = e.get(type_key) if type_key else None
        if undirected:
            ka, kb = str(kind_of(a)), str(kind_of(b))
            if (ka, a) > (kb, b):  # orient by (kind, id): kind a side first
                a, b, ka, kb = b, a, kb, ka
            ck = (_jkey(ty), ka, kb)
        else:
            ck = (_jkey(ty), str(kind_of(a)), str(kind_of(b)))
        units.setdefault((a, b), (ck, ty, []))[2].append(_attrs(e))
    order = sorted(units)
    classes = sorted({units[p][0] for p in order})
    cidx = {c: i for i, c in enumerate(classes)}
    pairs = [list(p) for p in order]
    cls = [cidx[units[p][0]] for p in order]
    same_kind = [c[1] == c[2] for c in classes]

    # attributes constant within each class are copied to the rewired edges
    const, dropped = [], set()
    for ci in range(len(classes)):
        recs = [a for p in order if cidx[units[p][0]] == ci for a in units[p][2]]
        names = set().union(*(r.keys() for r in recs)) if recs else set()
        keep = {}
        for k in sorted(names):
            vals = {_jkey(r.get(k, None)) if k in r else "<absent>" for r in recs}
            if len(vals) == 1 and "<absent>" not in vals:
                keep[k] = recs[0][k]
            else:
                dropped.add(k)
        const.append(keep)

    n_e = len(pairs)
    nswap = int(round(factor * n_e))
    max_tries = max(int(round(max_tries_factor * n_e)), nswap)
    use_nx = engine == "networkx" or (engine == "auto" and undirected and len(classes) == 1 and same_kind[0])
    if engine == "networkx" and not (len(classes) == 1 and same_kind[0]):
        raise ValueError("engine='networkx' needs a single swap class with equal endpoint kinds")
    error = None
    if n_e == 0:
        swaps, tries, name = Counter(), 0, "none"
    elif use_nx:
        name = "networkx." + ("double_edge_swap" if undirected else "directed_edge_swap")
        pairs, error = _nx_swap(pairs, nswap, max_tries, seed, undirected)
        cls = [0] * len(pairs)
        swaps, tries = None, None
    else:
        name = "constrained_" + ("double_edge_swap" if undirected else "two_edge_directed_swap")
        swaps, tries = _swap_loop(pairs, cls, same_kind, nswap, max_tries, random.Random(seed), undirected)

    out = []
    for (a, b), ci in zip(pairs, cls):
        out.append({"source": a, "target": b, **const[ci]})
        if undirected:
            out.append({"source": b, "target": a, **const[ci]})
    out.extend(dict(e) for e in loops)
    out.sort(key=lambda e: (e["source"], e["target"]))

    key = (lambda a, b: (a, b) if a <= b else (b, a)) if undirected else (lambda a, b: (a, b))
    old_keys = {key(*p) for p in order}
    new_keys = [key(*p) for p in pairs]
    by_class_old = Counter(units[p][0] for p in order)
    class_rows = []
    for ci, c in enumerate(classes):
        old_c = {key(*p) for p in order if units[p][0] == c}
        new_c = [k for k, x in zip(new_keys, cls) if x == ci]
        class_rows.append({
            "type": json.loads(c[0]), "kinds": [c[1], c[2]], "n_edges": by_class_old[c],
            "swaps": (swaps.get(ci, 0) if swaps is not None else None),
            "edge_overlap": (sum(k in old_c for k in new_c) / len(new_c)) if new_c else None,
        })
    swaps_done = sum(swaps.values()) if swaps is not None else None
    report = {
        "rewire_version": REWIRE_VERSION,
        "networkx_version": nx.__version__,
        "mode": "mirrored" if undirected else "directed",
        "input_mirrored": mirrored,
        "engine": name,
        "seed": seed,
        "factor": factor,
        "max_tries_factor": max_tries_factor,
        "n_edges_in": len(edges),
        "n_swapped_edges": n_e,
        "self_loops": len(loops),
        "nswap": nswap,
        "max_tries": max_tries,
        "swaps_done": swaps_done,
        "tries": tries,
        "completed": (error is None) if use_nx else (swaps_done == nswap),
        "error": error,
        "edge_overlap": (sum(k in old_keys for k in new_keys) / n_e) if n_e else None,
        "classes": class_rows,
        "copied_edge_attrs": sorted(set().union(*(c.keys() for c in const))) if const else [],
        "dropped_edge_attrs": sorted(dropped),
    }
    return out, report


def rewire_graph(graph: dict, links_key: str = "links", kind_key: str | None = None,
                 type_key: str | None = "type", group_key: str | None = None, **kw):
    """Rewire a node-link graph dict. Nodes are copied unchanged. Returns (new graph, report)."""
    node_ids = {n["id"] for n in graph["nodes"]}
    kinds = {n["id"]: n.get(kind_key) for n in graph["nodes"]} if kind_key else {}
    kind_of = (lambda x: kinds.get(x)) if kind_key else None
    edges = graph[links_key]
    new_edges, rep = rewire_edges(edges, kind_of=kind_of, type_key=type_key, **kw)
    rep["kind_key"] = kind_key
    rep["missing_endpoints"] = sum((e["source"] not in node_ids) + (e["target"] not in node_ids)
                                   for e in edges)
    rep["invariants"] = check_invariants(edges, new_edges, kind_of, type_key)
    if group_key:
        groups = {n["id"]: n.get(group_key) for n in graph["nodes"]}
        rep["same_group_share"] = {"key": group_key,
                                   "before": same_group_share(edges, groups.get),
                                   "after": same_group_share(new_edges, groups.get)}
    g = json.loads(json.dumps(graph))
    g[links_key] = new_edges
    g.setdefault("graph", {})["rewired"] = {k: rep[k] for k in (
        "rewire_version", "networkx_version", "mode", "engine", "seed", "factor", "nswap",
        "swaps_done", "completed", "edge_overlap")}
    return g, rep


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Degree-preserving rewiring of a node-link call graph.")
    ap.add_argument("graph", help="node-link JSON (ngraph.extract format or an adapted official graph)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", help="write the rewiring report (JSON) here")
    ap.add_argument("--links-key", default="links")
    ap.add_argument("--kind-key", help="node attribute holding the node kind (e.g. library/test/doc)")
    ap.add_argument("--type-key", default="type", help="edge attribute holding the edge type ('' for none)")
    ap.add_argument("--group-key", help="node attribute for the same-group diagnostic (e.g. module)")
    ap.add_argument("--mirror-first", action="store_true",
                    help="build the official-like mirrored view (ngraph.extract.mirrored) before rewiring")
    ap.add_argument("--mode", default="auto", choices=("auto", "mirrored", "directed"))
    ap.add_argument("--engine", default="auto", choices=("auto", "networkx", "constrained"))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--factor", type=float, default=10)
    ap.add_argument("--max-tries-factor", type=float, default=100)
    args = ap.parse_args(argv)
    for path in (args.out, args.report):  # a fresh copy has no runs/ folder
        if path:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    with open(args.graph) as fh:
        g = json.load(fh)
    if args.mirror_first:
        from ngraph.extract import mirrored
        g = mirrored(g, args.links_key)
    g2, rep = rewire_graph(g, links_key=args.links_key, kind_key=args.kind_key,
                           type_key=args.type_key or None, group_key=args.group_key,
                           mode=args.mode, engine=args.engine, seed=args.seed,
                           factor=args.factor, max_tries_factor=args.max_tries_factor)
    with open(args.out, "w") as fh:
        json.dump(g2, fh, indent=1)
    rep["input_file"] = {"path": args.graph, "sha256": _sha256(args.graph), "mirror_first": args.mirror_first}
    rep["output_file"] = {"path": args.out, "sha256": _sha256(args.out)}
    if args.report:
        with open(args.report, "w") as fh:
            json.dump(rep, fh, indent=1)
    inv = rep["invariants"]
    print(f"{args.graph}: {rep['mode']} {rep['engine']}, {rep['n_swapped_edges']} edges, "
          f"swaps {rep['swaps_done']}/{rep['nswap']}, overlap {rep['edge_overlap']}, "
          f"invariants {'ok' if inv['all_ok'] else 'FAILED'}")
    return 0 if inv["all_ok"] and rep["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

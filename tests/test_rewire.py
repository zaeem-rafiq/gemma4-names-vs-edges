"""Tests for degree-preserving rewiring (Study B, "rewired" condition)."""

import json
import os
import random
from collections import Counter

import pytest

from ngraph import rewire as rw
from ngraph.extract import mirrored

GRAPHS = os.environ.get("NGRAPH_GRAPHS_DIR", "")


def _skewed_pairs(n, m, seed, directed=False):
    """Random simple graph with hubs (endpoint weights fall off with node index)."""
    rng = random.Random(seed)
    nodes = [f"pkg.m{i % 7}.f{i:04d}" for i in range(n)]
    w = [1.0 / (i + 1) ** 0.7 for i in range(n)]
    pairs = set()
    while len(pairs) < m:
        a, b = rng.choices(nodes, w, k=2)
        if a == b:
            continue
        if not directed:
            a, b = min(a, b), max(a, b)
        pairs.add((a, b))
    return nodes, sorted(pairs)


def _mirrored_edges(pairs, etype="calls"):
    return [{"source": a, "target": b, "type": etype} for a, b in pairs] + \
           [{"source": b, "target": a, "type": etype} for a, b in pairs]


def _kinds(nodes, seed, kinds=("library", "test", "doc"), p=(0.3, 0.6, 0.1)):
    rng = random.Random(seed)
    return {v: rng.choices(kinds, p)[0] for v in nodes}


def test_mirrored_with_kinds_uses_constrained_swaps():
    nodes, pairs = _skewed_pairs(300, 900, seed=0)
    kind = _kinds(nodes, 1)
    edges = _mirrored_edges(pairs)
    out, rep = rw.rewire_edges(edges, kind_of=kind.get, seed=1)
    inv = rw.check_invariants(edges, out, kind.get)
    assert rep["mode"] == "mirrored" and rep["engine"] == "constrained_double_edge_swap"
    assert rep["completed"] and rep["swaps_done"] == rep["nswap"] == 10 * len(pairs)
    assert inv["all_ok"] and inv["reciprocity_before"] == inv["reciprocity_after"] == 1.0
    assert rep["edge_overlap"] < 0.5
    assert len(rep["classes"]) == 6 and sum(c["n_edges"] for c in rep["classes"]) == len(pairs)
    out2, _ = rw.rewire_edges(edges, kind_of=kind.get, seed=1)
    out3, _ = rw.rewire_edges(list(reversed(edges)), kind_of=kind.get, seed=1)
    out4, _ = rw.rewire_edges(edges, kind_of=kind.get, seed=2)
    assert out == out2 == out3 and out != out4


def test_mirrored_single_class_uses_networkx():
    nodes, pairs = _skewed_pairs(200, 500, seed=3)
    edges = _mirrored_edges(pairs)
    out, rep = rw.rewire_edges(edges, seed=1)
    assert rep["engine"] == "networkx.double_edge_swap" and rep["completed"] and rep["error"] is None
    inv = rw.check_invariants(edges, out)
    assert inv["all_ok"] and inv["reciprocity_after"] == 1.0
    assert rep["edge_overlap"] < 0.5
    assert out == rw.rewire_edges(list(reversed(edges)), seed=1)[0]
    # forcing the constrained loop on the same graph keeps the same invariants
    out_c, rep_c = rw.rewire_edges(edges, seed=1, engine="constrained")
    assert rep_c["engine"] == "constrained_double_edge_swap" and rw.check_invariants(edges, out_c)["all_ok"]


def test_directed_graph_uses_two_edge_swaps():
    nodes, pairs = _skewed_pairs(200, 600, seed=4, directed=True)
    edges = [{"source": a, "target": b, "type": "calls"} for a, b in pairs]
    assert not rw.is_mirrored(edges)
    out, rep = rw.rewire_edges(edges, seed=1)
    assert rep["mode"] == "directed" and rep["engine"] == "constrained_two_edge_directed_swap"
    assert rep["completed"] and rep["swaps_done"] == rep["nswap"] == 10 * len(pairs)
    assert rw.check_invariants(edges, out)["all_ok"]
    assert rep["edge_overlap"] < 0.2
    assert out == rw.rewire_edges(list(reversed(edges)), seed=1)[0]
    # networkx's three-edge swaps stay available on request and keep the same invariants
    out_n, rep_n = rw.rewire_edges(edges, seed=1, engine="networkx")
    assert rep_n["engine"] == "networkx.directed_edge_swap" and rw.check_invariants(edges, out_n)["all_ok"]


def test_directed_with_kinds_and_two_edge_types():
    nodes, pairs = _skewed_pairs(250, 800, seed=5, directed=True)
    kind = _kinds(nodes, 6)
    rng = random.Random(7)
    edges = [{"source": a, "target": b, "type": rng.choice(["calls", "imports"])} for a, b in pairs]
    out, rep = rw.rewire_edges(edges, kind_of=kind.get, seed=1)
    assert rep["engine"] == "constrained_two_edge_directed_swap" and rep["completed"]
    inv = rw.check_invariants(edges, out, kind.get)
    assert inv["all_ok"]
    assert Counter(e["type"] for e in out) == Counter(e["type"] for e in edges)
    assert rep["edge_overlap"] < 0.6


def test_mixed_kind_class_keeps_bipartite_structure():
    rng = random.Random(8)
    lib = [f"lib.f{i}" for i in range(40)]
    tests = [f"tests.t{i}" for i in range(120)]
    pairs = sorted({(rng.choice(lib), rng.choice(tests)) for _ in range(400)})
    kind = {**{v: "library" for v in lib}, **{v: "test" for v in tests}}
    edges = _mirrored_edges(pairs)
    out, rep = rw.rewire_edges(edges, kind_of=kind.get, seed=1)
    # one swap class, but its kinds differ, so networkx's double_edge_swap must not be used
    assert len(rep["classes"]) == 1 and rep["engine"] == "constrained_double_edge_swap"
    assert all(kind[e["source"]] != kind[e["target"]] for e in out)
    assert rw.check_invariants(edges, out, kind.get)["all_ok"]
    with pytest.raises(ValueError):
        rw.rewire_edges(edges, kind_of=kind.get, engine="networkx")


def test_unswappable_graph_is_reported_not_raised():
    k4 = [(a, b) for a in "abcd" for b in "abcd" if a < b]
    edges = _mirrored_edges(k4)
    out, rep = rw.rewire_edges(edges, seed=1)
    assert rep["engine"] == "networkx.double_edge_swap" and not rep["completed"]
    assert "NetworkXAlgorithmError" in rep["error"]
    assert sorted((e["source"], e["target"]) for e in out) == sorted((e["source"], e["target"]) for e in edges)
    out_c, rep_c = rw.rewire_edges(edges, seed=1, engine="constrained")
    assert rep_c["swaps_done"] == 0 and rep_c["tries"] == rep_c["max_tries"] and not rep_c["completed"]
    tiny = _mirrored_edges([("a", "b"), ("b", "c")])  # three nodes: networkx refuses
    _, rep_t = rw.rewire_edges(tiny, seed=1)
    assert not rep_t["completed"] and "NetworkXError" in rep_t["error"]


def test_self_loops_and_edge_attributes():
    nodes, pairs = _skewed_pairs(60, 150, seed=9)
    edges = []
    for i, (a, b) in enumerate(pairs):
        for s, t in ((a, b), (b, a)):
            edges.append({"source": s, "target": t, "type": "calls", "origin": "static", "weight": i % 3})
    edges.append({"source": nodes[0], "target": nodes[0], "type": "calls", "weight": 9})
    out, rep = rw.rewire_edges(edges, seed=1)
    assert rep["self_loops"] == 1 and rep["mode"] == "mirrored"
    assert {"source": nodes[0], "target": nodes[0], "type": "calls", "weight": 9} in out
    assert rep["copied_edge_attrs"] == ["origin", "type"] and rep["dropped_edge_attrs"] == ["weight"]
    assert all(e.get("origin") == "static" and "weight" not in e for e in out if e["source"] != e["target"])
    inv = rw.check_invariants(edges, out)
    assert inv["all_ok"] and inv["self_loops_unchanged"]


def test_input_checks():
    dup = [{"source": "a", "target": "b"}, {"source": "a", "target": "b"}]
    with pytest.raises(ValueError):
        rw.rewire_edges(dup)
    one_way = [{"source": "a", "target": "b", "type": "calls"}, {"source": "c", "target": "d", "type": "calls"},
               {"source": "d", "target": "c", "type": "calls"}]
    with pytest.raises(ValueError):
        rw.rewire_edges(one_way, mode="mirrored")
    typed = [{"source": "a", "target": "b", "type": "calls"}, {"source": "b", "target": "a", "type": "imports"}]
    assert not rw.is_mirrored(typed) and rw.is_mirrored(typed, type_key=None)
    assert rw.reciprocity([]) is None and rw.reciprocity([("a", "b"), ("b", "a"), ("a", "c")]) == pytest.approx(2 / 3)


def _graph_doc(pairs, nodes):
    return {"directed": True, "multigraph": False, "graph": {"repo": "toy"},
            "nodes": [{"id": v, "kind": "function", "module": v.rsplit(".", 1)[0]} for v in nodes],
            "links": [{"source": a, "target": b, "type": "calls"} for a, b in pairs]}


def test_cli_writes_graph_and_report(tmp_path):
    nodes, pairs = _skewed_pairs(120, 300, seed=10, directed=True)
    src = tmp_path / "g.json"
    src.write_text(json.dumps(_graph_doc(pairs, nodes)))
    out, rep = tmp_path / "runs" / "g_rewired.json", tmp_path / "reports" / "rep.json"  # new folders are made
    code = rw.main([str(src), "--out", str(out), "--report", str(rep), "--mirror-first", "--group-key", "module"])
    assert code == 0
    g2, r = json.loads(out.read_text()), json.loads(rep.read_text())
    assert r["mode"] == "mirrored" and r["invariants"]["all_ok"] and r["completed"]
    assert g2["nodes"] == _graph_doc(pairs, nodes)["nodes"] and g2["graph"]["rewired"]["seed"] == 1
    assert r["output_file"]["sha256"] == rw._sha256(str(out)) and len(r["input_file"]["sha256"]) == 64
    assert r["same_group_share"]["key"] == "module"


@pytest.mark.skipif(not (GRAPHS and os.path.isdir(GRAPHS)), reason="set NGRAPH_GRAPHS_DIR")
@pytest.mark.parametrize("repo", ["requests", "flask", "nanobot"])
def test_rewire_extracted_graphs(repo):
    with open(os.path.join(GRAPHS, f"{repo}.json")) as fh:
        g = mirrored(json.load(fh))
    g2, rep = rw.rewire_graph(g, group_key="module", seed=1)
    assert rep["mode"] == "mirrored" and rep["completed"] and rep["invariants"]["all_ok"]
    assert rep["invariants"]["reciprocity_after"] == 1.0 and rep["missing_endpoints"] == 0
    assert rep["same_group_share"]["after"] < rep["same_group_share"]["before"]
    assert g2["nodes"] == g["nodes"]


@pytest.mark.skipif(not (GRAPHS and os.path.isdir(GRAPHS)), reason="set NGRAPH_GRAPHS_DIR")
@pytest.mark.parametrize("repo", ["requests", "flask", "nanobot"])
def test_rewire_extracted_graphs_directed(repo):
    with open(os.path.join(GRAPHS, f"{repo}.json")) as fh:
        g = json.load(fh)
    g2, rep = rw.rewire_graph(g, group_key="module", seed=1)
    assert rep["mode"] == "directed" and rep["engine"] == "constrained_two_edge_directed_swap"
    assert rep["completed"] and rep["invariants"]["all_ok"] and rep["missing_endpoints"] == 0
    assert rep["edge_overlap"] < 0.15
    assert rep["same_group_share"]["after"] < rep["same_group_share"]["before"]


def test_invariant_checker_catches_violations():
    rng = random.Random(11)
    lib = [f"lib.f{i}" for i in range(30)]
    tests = [f"tests.t{i}" for i in range(90)]
    pairs = sorted({(rng.choice(lib), rng.choice(tests)) for _ in range(300)})
    kind = {**{v: "library" for v in lib}, **{v: "test" for v in tests}}
    edges = _mirrored_edges(pairs)
    # unconstrained networkx swaps on a library-test graph create library-library edges
    swapped, err = rw._nx_swap([list(p) for p in pairs], 3000, 30000, 1, True)
    assert err is None
    bad = _mirrored_edges(swapped)
    inv = rw.check_invariants(edges, bad, kind.get)
    assert inv["degrees_equal"] and not inv["neighbour_kind_mix_equal"] and not inv["all_ok"]
    moved = [dict(e) for e in edges]
    moved[0]["target"] = next(v for v in tests if v != moved[0]["target"])
    assert not rw.check_invariants(edges, moved, kind.get)["degrees_equal"]
    retyped = [dict(e) for e in edges]
    retyped[0]["type"] = "imports"
    assert not rw.check_invariants(edges, retyped, kind.get)["edge_type_counts_equal"]
    assert not rw.check_invariants(edges, edges + [edges[0]], kind.get)["no_parallel_edges"]

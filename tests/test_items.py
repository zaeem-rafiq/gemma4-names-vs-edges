"""Invariant tests for Study A items (manipulation check MC1 and the leak part of MC2).

Run on a toy graph always, and on every generated item file found in $NGRAPH_ITEMS_DIR
(each item file must sit next to its graph file in $NGRAPH_GRAPHS_DIR, same basename).
"""

import glob
import json
import os
import re
from collections import Counter

import pytest

from ngraph.extract import extract
from ngraph.items import Graph, generate, correct_set, induced, LETTERS, HEADER, Q_A, Q_B, FOOTER
from ngraph.names import split_subtokens, STD_DUNDERS, approx_token_count, offensive, WHOLE_WORD_BLOCKED

HERE = os.path.dirname(__file__)
ITEMS_DIR = os.environ.get("NGRAPH_ITEMS_DIR")
GRAPHS_DIR = os.environ.get("NGRAPH_GRAPHS_DIR")


def _toy_repo(tmp_path):
    pkg = tmp_path / "toypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("from .core import run\n")
    (pkg / "core.py").write_text(
        "from .util import helper, fmt\n"
        "from . import util\n\n"
        "class Base:\n"
        "    def __init__(self):\n        self.setup()\n"
        "    def setup(self):\n        return helper(1)\n"
        "    def shared(self):\n        return fmt('x')\n\n"
        "class Child(Base):\n"
        "    def go(self):\n        self.shared()\n        return super().setup()\n"
        "    def other(self):\n        return util.fmt('y')\n\n"
        "def run():\n    c = Child()\n    c.go()\n    return make()\n\n"
        "def make():\n    return Child()\n\n"
        "def shadowed(helper):\n    return helper(2)\n\n"
        "def local_import():\n    from .util import fmt as f2\n    return f2('z')\n"
    )
    (pkg / "util.py").write_text(
        "def helper(x):\n    return fmt(str(x))\n\n"
        "def fmt(s):\n    return s.strip()\n\n"
        "def unused():\n    return helper(3)\n"
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_core.py").write_text("from toypkg.core import run\n\ndef test_run():\n    run()\n")
    return tmp_path


def test_extractor_rules_on_toy_repo(tmp_path):
    root = _toy_repo(tmp_path)
    g = extract(str(root), "toy")
    edges = {(e["source"], e["target"]) for e in g["links"]}
    expect = {
        ("toypkg.core.Base.__init__", "toypkg.core.Base.setup"),        # self.m
        ("toypkg.core.Base.setup", "toypkg.util.helper"),               # imported function
        ("toypkg.core.Base.shared", "toypkg.util.fmt"),
        ("toypkg.core.Child.go", "toypkg.core.Base.shared"),            # self.m via in-repo base
        ("toypkg.core.Child.go", "toypkg.core.Base.setup"),             # super().m
        ("toypkg.core.Child.other", "toypkg.util.fmt"),                 # module attribute
        ("toypkg.core.run", "toypkg.core.Base.__init__"),               # constructor via base __init__
        ("toypkg.core.run", "toypkg.core.make"),
        ("toypkg.core.make", "toypkg.core.Base.__init__"),
        ("toypkg.core.local_import", "toypkg.util.fmt"),                # function-local import
        ("toypkg.util.helper", "toypkg.util.fmt"),
        ("toypkg.util.unused", "toypkg.util.helper"),
    }
    assert expect <= edges, sorted(expect - edges)
    # c.go() on a local variable is not resolved; a parameter named like a function shadows it
    assert ("toypkg.core.run", "toypkg.core.Child.go") not in edges
    assert ("toypkg.core.shadowed", "toypkg.util.helper") not in edges
    # tests are excluded from the node set
    assert not any(n["path"].startswith("tests/") for n in g["nodes"])


def _item_files():
    if not ITEMS_DIR:
        return []
    return sorted(glob.glob(os.path.join(ITEMS_DIR, "*.json")))


def _check_item(item, G):
    opts = item["options"]
    assert len(opts) == 4 and len(set(opts)) == 4
    B, C, focal, qt = item["answer_true"], item["answer_swapped"], item["focal"], item["qtype"]
    assert B != C and focal not in opts
    roles = item["roles"]
    assert roles[B] == "answer" and roles[C] == "swap_partner"
    S = item["nodes"]
    assert len(S) == len(set(S)) == item["size_target"]
    true_e = {tuple(e) for e in item["edges_true"]}
    sw_e = {tuple(e) for e in item["edges_swapped"]}
    # shown true edges are exactly the induced edges of the full graph
    assert true_e == induced(G, S)
    # no self-loops; swapped graph differs by exactly the registered swap
    assert all(s != t for s, t in true_e | sw_e)
    rem = {tuple(e) for e in item["swap"]["remove"]}
    add = {tuple(e) for e in item["swap"]["add"]}
    assert true_e - sw_e == rem and sw_e - true_e == add and len(rem) == len(add) == 2
    # degrees preserved for every shown node
    for d in (0, 1):
        assert Counter(e[d] for e in true_e) == Counter(e[d] for e in sw_e)
    # exactly one correct option in each shown graph
    assert correct_set(qt, true_e, focal, opts) == {B}
    assert correct_set(qt, sw_e, focal, opts) == {C}
    # distractors are wrong in the FULL graph too (true versions never contradict the code)
    full = {(s, t) for s in G.nodes for t in G.out[s]}
    assert correct_set(qt, full, focal, opts) == {B}
    # letters
    perm_opts = [opts[i] for i in item["perm"]]
    v = item["versions"]
    for k in ("G0", "G1", "G2"):
        assert v[k]["correct"] == LETTERS[perm_opts.index(B)]
    for k in ("G3", "G4"):
        assert v[k]["correct"] == LETTERS[perm_opts.index(C)]
    # second option order (used for E2B and E4B): same texts apart from the option block
    v2 = item["versions_perm2"]
    perm2_opts = [opts[i] for i in item["perm2"]]
    for k in ("G0", "G1", "G2"):
        assert v2[k]["correct"] == LETTERS[perm2_opts.index(B)]
    for k in ("G3", "G4"):
        assert v2[k]["correct"] == LETTERS[perm2_opts.index(C)]
    for k in v:
        a_lines = [x for x in v[k]["text"].splitlines() if not re.match(r"^[ABCD]\. ", x)]
        b_lines = [x for x in v2[k]["text"].splitlines() if not re.match(r"^[ABCD]\. ", x)]
        assert a_lines == b_lines
    # G1 vs G3: exactly two graph lines differ
    l1, l3 = v["G1"]["text"].splitlines(), v["G3"]["text"].splitlines()
    assert len(l1) == len(l3)
    assert sum(a != b for a, b in zip(l1, l3)) == 2
    # G1 vs G2: same line structure; mapping names through neutral_map turns G1 lines into G2 lines
    nm = item["neutral_map"]
    l2 = v["G2"]["text"].splitlines()
    assert len(l1) == len(l2)
    qn_re = re.compile(r"[A-Za-z_][\w-]*(?:\.[A-Za-z_][\w-]*)+")
    for a, b in zip(l1, l2):
        if re.match(r"^[\w.-]+ -> ", a) or re.match(r"^[ABCD]\. ", a):
            mapped = qn_re.sub(lambda m: ".".join(nm[c] for c in m.group(0).split(".")), a)
            assert mapped == b, (a, b)
    # no leak: renamed components never contain an original sub-token. Only Python's own
    # protocol names (STD_DUNDERS) are kept; project dunders such as __rich__ are renamed.
    forbidden = set()
    for q in S:
        for c in q.split("."):
            forbidden |= {t for t in split_subtokens(c) if len(t) >= 3}
    forbidden |= {t for t in split_subtokens(G.repo or "") if len(t) >= 3}
    is_dunder = lambda s: s.startswith("__") and s.endswith("__") and len(s) > 4  # noqa: E731
    for orig, new in nm.items():
        if orig in STD_DUNDERS:
            assert new == orig
            continue
        assert new != orig and is_dunder(new) == is_dunder(orig), (orig, new)
        low = new.lower()
        assert not any(t in low for t in forbidden), (orig, new)
    # every name shown in G2 is either a kept protocol name or a mapped pseudo-word
    for q in S:
        assert all(nm[c] in STD_DUNDERS or nm[c] != c for c in q.split("."))
    # the repository name does not appear in the neutral versions (unless the fixed template contains it)
    template = " ".join([HEADER, Q_A, Q_B, FOOTER]).lower()
    if G.repo and G.repo.lower() not in template:
        for k in ("G2", "G4"):
            assert G.repo.lower() not in v[k]["text"].lower(), k


def test_setattr_rule(tmp_path):
    """Extractor 0.3.0: a literal setattr name blocks only that name; a name expression blocks every
    self.m() call of the class and its subclasses, except in __setstate__; static methods are ignored."""
    pkg = tmp_path / "sa"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "m.py").write_text(
        "class Literal:\n"
        "    def __init__(self):\n        setattr(self, 'lock', None)\n        self.run()\n        self.lock()\n"
        "    def run(self):\n        return 1\n"
        "    def lock(self):\n        return 2\n\n"
        "class Restore:\n"
        "    def __setstate__(self, state):\n        for k, v in state.items():\n            setattr(self, k, v)\n"
        "    def go(self):\n        return self.run()\n"
        "    def run(self):\n        return 1\n\n"
        "class Dynamic:\n"
        "    def configure(self, name, fn):\n        setattr(self, name, fn)\n"
        "    def go(self):\n        return self.run()\n"
        "    def run(self):\n        return 1\n\n"
        "class SubOfDynamic(Dynamic):\n"
        "    def again(self):\n        return self.run()\n\n"
        "class Static:\n"
        "    @staticmethod\n    def fill(obj, name):\n        setattr(obj, name, 1)\n"
        "    def go(self):\n        return self.run()\n"
        "    def run(self):\n        return 1\n\n"
        "class ClassLevel:\n"
        "    @classmethod\n    def patch(cls, name):\n        setattr(cls, name, None)\n"
        "    def go(self):\n        return self.run()\n"
        "    def run(self):\n        return 1\n"
    )
    g = extract(str(tmp_path), "sa")
    edges = {(e["source"], e["target"]) for e in g["links"]}
    assert ("sa.m.Literal.__init__", "sa.m.Literal.run") in edges
    assert ("sa.m.Literal.__init__", "sa.m.Literal.lock") not in edges
    assert ("sa.m.Restore.go", "sa.m.Restore.run") in edges
    assert ("sa.m.Dynamic.go", "sa.m.Dynamic.run") not in edges
    assert ("sa.m.SubOfDynamic.again", "sa.m.Dynamic.run") not in edges
    assert ("sa.m.Static.go", "sa.m.Static.run") in edges
    assert ("sa.m.ClassLevel.go", "sa.m.ClassLevel.run") not in edges


@pytest.mark.parametrize("repo", ["requests", "httpx", "daily_stock_analysis", "nanobot"])
def test_stored_items_match_regenerated_graphs(repo):
    """The four repositories whose graphs changed with extractor 0.3.0: their stored questions are
    exactly what the generator makes from the stored graphs."""
    path = os.path.join(ITEMS_DIR or "", repo + ".json")
    if not (GRAPHS_DIR and os.path.exists(path)):
        pytest.skip("set NGRAPH_ITEMS_DIR and NGRAPH_GRAPHS_DIR")
    g = json.load(open(os.path.join(GRAPHS_DIR, repo + ".json")))
    assert g["graph"]["extractor_version"] == "0.3.0"
    stored = json.load(open(path))
    res = generate(g, count_tokens=_counter_for(stored))
    assert json.dumps(res, sort_keys=True) == json.dumps(stored, sort_keys=True)


@pytest.mark.parametrize("path", _item_files())
def test_generated_items(path):
    data = json.load(open(path))
    gpath = os.path.join(GRAPHS_DIR, os.path.basename(path))
    G = Graph(json.load(open(gpath)))
    assert data["n_items"] == len(data["items"]) > 0
    focals = [it["focal"] for it in data["items"]]
    assert len(focals) == len(set(focals))
    for item in data["items"]:
        _check_item(item, G)


def _counter_for(stored):
    """The token counter the stored items were built with (the Gemma 4 vocab file, checked by SHA-256)."""
    if stored.get("token_counter") != "gemma4_gguf_tokenizer":
        return approx_token_count
    path = os.environ.get("NGRAPH_TOKENIZER_GGUF")
    if not (path and os.path.exists(path)):
        pytest.skip("items were built with the Gemma 4 tokenizer; set NGRAPH_TOKENIZER_GGUF")
    pytest.importorskip("llama_cpp")
    from ngraph.tok import GemmaCounter

    counter = GemmaCounter(path)
    assert counter.record() == stored["token_counter_file"]
    return counter


@pytest.mark.parametrize("path", _item_files()[:3])
def test_generation_is_deterministic(path):
    gpath = os.path.join(GRAPHS_DIR, os.path.basename(path))
    g = json.load(open(gpath))
    stored = json.load(open(path))
    counter = _counter_for(stored)
    a = generate(g, count_tokens=counter)
    b = generate(g, count_tokens=counter)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert json.dumps(a["items"], sort_keys=True) == json.dumps(stored["items"], sort_keys=True)


def test_toy_items(tmp_path):
    root = _toy_repo(tmp_path)
    g = extract(str(root), "toy")
    G = Graph(g)
    res = generate(g, per_cell=2, sizes=(6,))
    for item in res["items"]:
        _check_item(item, G)


def test_common_word_filter_bars():
    from ngraph.items import common_word_filter

    rej = common_word_filter(3.0)
    for w in ("to", "of", "be", "go", "no", "re", "id", "get", "request", "session"):
        assert rej(w), w
    for w in ("zi", "zo", "pu", "vusket", "ralmo"):
        assert not rej(w), w


@pytest.mark.parametrize("path", _item_files())
def test_neutral_names_avoid_common_words(path):
    from ngraph.items import common_word_filter

    data = json.load(open(path))
    cfg = data.get("common_word_filter")
    if not cfg:
        pytest.skip("items generated without the common-word filter")
    rej = common_word_filter(cfg["zipf_min"], cfg.get("zipf_min_two_letters", cfg["zipf_min"]))
    for item in data["items"]:
        for w in item["neutral_subtoken_map"].values():
            assert len(w) == 1 or not rej(w), (item["item_id"], w)
        for real, new in item["neutral_map"].items():
            if real in STD_DUNDERS:
                continue
            for p in re.split(r"[_-]", new):
                assert not (len(p) > 1 and p.isalpha() and rej(p.lower())), (item["item_id"], new)


@pytest.mark.parametrize("path", _item_files())
def test_neutral_names_avoid_offensive_substrings(path):
    data = json.load(open(path))
    for item in data["items"]:
        names = list(item["neutral_subtoken_map"].values()) + [item["neutral_repo"]]
        names += [new for real, new in item["neutral_map"].items() if real not in STD_DUNDERS]
        assert not [n for n in names if offensive(n)], item["item_id"]
        whole = [w for w in item["neutral_subtoken_map"].values() if w.lower() in WHOLE_WORD_BLOCKED]
        assert not whole, item["item_id"]


def test_blocked_strings_the_generator_cannot_write():
    import ngraph.names as nm

    letters = set(nm.CONSONANTS + nm.VOWELS)
    assert sorted(b for b in nm.OFFENSIVE_SUBSTRINGS if not set(b) <= letters) == sorted(nm.UNWRITABLE_BLOCKED)


def test_whole_word_blocked_names_are_drawn_again(tmp_path, monkeypatch):
    import ngraph.items as itm

    assert WHOLE_WORD_BLOCKED == ("fok", "pula")
    g = extract(str(_toy_repo(tmp_path)), "toy")
    before = generate(g, per_cell=2, sizes=(6,))
    # only a whole pseudo-word is blocked, so blocking a strict part of one changes nothing
    words = {w.lower() for it in before["items"] for w in it["neutral_subtoken_map"].values()}
    part = next(w[:-1] for w in sorted(words, key=lambda x: (-len(x), x))
                if len(w) > 3 and w[:-1] not in words)
    monkeypatch.setattr(itm, "WHOLE_WORD_BLOCKED", (part,))
    again = generate(g, per_cell=2, sizes=(6,))
    assert json.dumps(again, sort_keys=True) == json.dumps(before, sort_keys=True)
    word = max(before["items"][0]["neutral_subtoken_map"].values(), key=len).lower()  # treat as blocked
    monkeypatch.setattr(itm, "WHOLE_WORD_BLOCKED", (word,))
    after = generate(g, per_cell=2, sizes=(6,))
    first = after["items"][0]
    assert first.get("neutral_naming_attempt", 0) >= 1
    assert word not in [w.lower() for w in first["neutral_subtoken_map"].values()]
    _check_item(first, Graph(g))


def test_offensive_names_are_drawn_again(tmp_path, monkeypatch):
    import ngraph.names as nm

    assert offensive("Nazizes") and offensive("raper") and offensive("PEDO") and not offensive("kolu")
    assert offensive("nigu") and offensive("posmilfas") and offensive("disperme")
    # words split by "_" or "-" (the wider check of 8 Nov), and words the first list lacked
    assert offensive("kil_ra_pe") and offensive("kir-na_zi") and offensive("_Ni_Ga") and offensive("fuk")
    assert offensive("gorputo") and offensive("_pa_ki_ru") and not offensive("ko.ni.gol")
    assert offensive("ra-pe") and offensive("kir-na-zi")  # "-" alone also joins the parts
    assert offensive("pukin") and offensive("_pu_ki") and not offensive("fok") and not offensive("pula")
    g = extract(str(_toy_repo(tmp_path)), "toy")
    before = generate(g, per_cell=2, sizes=(6,))
    first = before["items"][0]
    word = max(first["neutral_subtoken_map"].values(), key=len)  # treat this pseudo-word as offensive
    monkeypatch.setattr(nm, "OFFENSIVE_SUBSTRINGS", (word,))
    after = generate(g, per_cell=2, sizes=(6,))
    assert [it["item_id"] for it in after["items"]] == [it["item_id"] for it in before["items"]]
    G = Graph(g)
    for a, b in zip(before["items"], after["items"]):
        names_a = list(a["neutral_subtoken_map"].values()) + list(a["neutral_map"].values()) + [a["neutral_repo"]]
        if any(word in n.lower() for n in names_a):  # named again with the next seeds
            assert b.get("neutral_naming_attempt", 0) >= 1
            assert not any(word in n.lower() for n in b["neutral_map"].values())
            _check_item(b, G)
        else:  # a question whose names are clean is unchanged
            assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert after["items"][0].get("neutral_naming_attempt", 0) >= 1
